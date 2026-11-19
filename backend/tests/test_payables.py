from decimal import Decimal

from fastapi.testclient import TestClient

from app.api import create_app
from app.sync import synchronize


def bill(external_id, total, payments=()):
    return {
        "id": external_id,
        "dueDate": "2026-12-01",
        "totalAmount": Decimal(total),
        "totalAmountCurrencyCode": "BRL",
        "payments": [{"paymentDate": "2026-11-19", "amount": Decimal(amount)} for amount in payments],
    }


def result(engine):
    with TestClient(create_app(engine)) as client:
        response = client.get("/payables")
        assert response.status_code == 200
        return response.json()


def test_subtracts_payments_and_excludes_settled_bills(engine, fake_client):
    fake_client.snapshot["bills"]["card"] = [
        bill("partial", "100.10", ["20.03", "30.02"]),
        bill("paid", "200", ["200"]),
        bill("overpaid", "10", ["15"]),
    ]
    synchronize(engine, fake_client, "item")
    data = result(engine)
    assert data["totals"] == [{"currency": "BRL", "amount": "100.17"}]  # 50.05 + 50.12
    assert data["statement_count"] == 1
    assert data["pending_purchase_count"] == 1
    assert data["boletos_available"] is False
    assert data["estimated"] is True


def test_linked_and_unresolved_bill_transactions_are_not_counted_twice(engine, fake_client):
    fake_client.snapshot["bills"]["card"] = [bill("bill", "50.12")]
    fake_client.snapshot["transactions"]["card"][0]["creditCardMetadata"]["billId"] = "bill"
    synchronize(engine, fake_client, "item")
    assert result(engine)["totals"] == [{"currency": "BRL", "amount": "50.12"}]
    fake_client.snapshot["transactions"]["card"][0]["creditCardMetadata"]["billId"] = "not-fetched"
    synchronize(engine, fake_client, "item")
    assert result(engine)["totals"] == [{"currency": "BRL", "amount": "50.12"}]


def test_refunds_offset_only_unbilled_same_currency_and_payment_is_not_subtracted_twice(engine, fake_client):
    original = fake_client.snapshot["transactions"]["card"][0]
    # PAGAMENTO can denote a purchase; only PAGAMENTO_FATURA is excluded.
    original["operationType"] = "PAGAMENTO"
    fake_client.snapshot["transactions"]["card"].extend(
        [
            {
                **original,
                "id": "refund",
                "type": "CREDIT",
                "amount": Decimal("-10.01"),
                "operationType": "ESTORNO",
            },
            {
                **original,
                "id": "payment",
                "type": "CREDIT",
                "amount": Decimal("-100"),
                "operationType": "PAGAMENTO_FATURA",
            },
            {**original, "id": "usd", "currencyCode": "USD", "amount": Decimal("9.99")},
        ]
    )
    synchronize(engine, fake_client, "item")
    assert result(engine)["totals"] == [
        {"currency": "BRL", "amount": "40.11"},
        {"currency": "USD", "amount": "9.99"},
    ]


def test_no_data_is_not_zero_and_bank_payments_are_not_boleto_debts(engine, fake_client):
    assert result(engine)["totals"] == []
    fake_client.snapshot["transactions"]["card"] = []
    fake_client.snapshot["transactions"]["bank"][0].update(status="PENDING", operationType="BOLETO")
    synchronize(engine, fake_client, "item")
    assert result(engine)["totals"] == [{"currency": "BRL", "amount": "0"}]


def test_foreign_purchase_uses_bank_conversion_when_available(engine, fake_client):
    tx = fake_client.snapshot["transactions"]["card"][0]
    tx.update(currencyCode="USD", amount=Decimal("10"), amountInAccountCurrency=Decimal("57.23"))
    synchronize(engine, fake_client, "item")
    assert result(engine)["totals"] == [{"currency": "BRL", "amount": "57.23"}]
    # Zero is a reported converted amount too, not a missing conversion.
    tx["amountInAccountCurrency"] = Decimal(0)
    synchronize(engine, fake_client, "item")
    assert result(engine)["totals"] == [{"currency": "BRL", "amount": "0"}]
