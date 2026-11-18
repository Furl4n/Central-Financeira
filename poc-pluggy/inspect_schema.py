"""Inspeciona apenas presença de campos e consistência; não exibe valores reais."""

import sys
from decimal import Decimal

from main import Client, ProbeError, load_config


def presence(rows, fields):
    return {field: sum(row.get(field) is not None for row in rows) for field in fields}


def inspect(client, config):
    client_id, secret, item_id = config
    payload = client.request("/auth", {"clientId": client_id, "clientSecret": secret})
    if not isinstance(payload.get("apiKey"), str):
        raise ProbeError("Autenticação sem token válido")
    client.key = payload["apiKey"]
    for account in client.records("/accounts", {"itemId": item_id}):
        kind = account.get("type")
        if kind not in ("BANK", "CREDIT"):
            print("Tipo de conta não contemplado nesta inspeção")
            continue
        print("Conta:", kind)
        credit = account.get("creditData") or {}
        print("Campos de limites:", presence([credit], (
            "creditLimit", "availableCreditLimit", "balanceDueDate", "balanceCloseDate",
            "minimumPayment", "disaggregatedCreditLimits")))
        params = {"accountId": account["id"]}
        transactions = list(client.records("/v2/transactions", params, cursor=True))
        print("Campos de transações:", presence(transactions, (
            "providerId", "operationType", "paymentData", "creditCardMetadata", "createdAt", "updatedAt")))
        metadata = [t.get("creditCardMetadata") or {} for t in transactions]
        print("Campos de parcelas:", presence(metadata, (
            "installmentNumber", "totalInstallments", "totalAmount", "purchaseDate", "billId", "paymentType")))
        for direction in ("DEBIT", "CREDIT"):
            amounts = [t["amount"] for t in transactions if t.get("type") == direction
                       and isinstance(t.get("amount"), (int, Decimal))]
            print(direction, "sinais (+, -, zero):", (
                sum(a > 0 for a in amounts), sum(a < 0 for a in amounts), sum(a == 0 for a in amounts)))
        print("Status conhecidos:", {status: sum(t.get("status") == status for t in transactions)
                                    for status in ("POSTED", "PENDING")})
        print("Pagamentos com marcador explícito:", sum(t.get("operationType") == "PAGAMENTO_FATURA" for t in transactions))
        if kind == "CREDIT":
            bills = list(client.records("/bills", params))
            bill_ids = {b["id"] for b in bills if b.get("id")}
            print("Vínculos de fatura presentes/encontrados:", (
                sum(bool(m.get("billId")) for m in metadata),
                sum(m.get("billId") in bill_ids for m in metadata)))
            payments = [p for b in bills for p in (b.get("payments") or [])]
            print("Campos de pagamentos de fatura:", presence(payments, (
                "paymentDate", "amount", "paymentMode", "valueType", "transactionId")))
            print("IDs de transação duplicados:", len(transactions) - len({t.get("id") for t in transactions}))


if __name__ == "__main__":
    try:
        inspect(Client(), load_config())
    except ProbeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
