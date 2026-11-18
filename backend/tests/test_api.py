from decimal import Decimal

from fastapi.testclient import TestClient

from app.api import create_app
from app.sync import synchronize


def test_read_api_pagination_filters_precision_and_card_sign(engine, fake_client):
    synchronize(engine, fake_client, "item")
    with TestClient(create_app(engine)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        accounts = client.get("/accounts", params={"type": "BANK"}).json()
        assert accounts["total"] == 1
        assert Decimal(accounts["items"][0]["balance"]) == Decimal("123.4567890123456789")
        txs = client.get("/transactions", params={"status": "PENDING", "limit": 1}).json()
        assert txs["total"] == 1
        assert txs["items"][0]["flow_amount"] == "-50.12"
        assert txs["items"][0]["raw_amount"] == "50.12"
        assert not txs["items"][0]["is_statement_payment"]
        assert (
            client.get("/transactions", params={"limit": 1, "offset": 1}).json()["items"][0]["description"]
            == "Compra fictícia"
        )
        assert client.get("/transactions", params={"date_from": "2026-11-11T00:00:00Z"}).json()["total"] == 1
        assert client.get("/statements").json()["total"] == 0
        status = client.get("/sync-status").json()[0]
        assert status["latest_execution"]["status"] == "SUCCEEDED"
        assert "external_id" not in status
        assert status["last_provider_update_at"] != status["last_successful_sync_at"]
        assert "external_id" not in accounts["items"][0]


def test_invalid_filters_and_no_write_endpoints(engine):
    with TestClient(create_app(engine)) as client:
        for params in (
            {"limit": 0},
            {"status": "INVALID"},
            {"account_id": "invalid"},
            {"date_from": "2026-11-01"},
            {"date_from": "2026-11-02T00:00:00Z", "date_to": "2026-11-01T00:00:00Z"},
        ):
            assert client.get("/transactions", params=params).status_code == 422
        assert client.post("/transactions").status_code == 405
