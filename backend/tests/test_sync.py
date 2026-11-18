import hashlib
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.models import Account, BankConnection, CardStatement, SyncExecution, Transaction, utcnow
from app.pluggy import SyncError
from app.sync import synchronize


def test_repeat_is_idempotent_and_decimal_is_exact(engine, fake_client):
    synchronize(engine, fake_client, "item")
    with Session(engine) as session:
        first_seen = session.scalar(select(Transaction.first_seen_at).limit(1))
    synchronize(engine, fake_client, "item")
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Transaction)) == 2
        assert session.scalar(select(func.count()).select_from(Account)) == 2
        assert session.scalar(select(Account.balance).where(Account.external_id == "bank")) == Decimal(
            "123.4567890123456789"
        )
        assert session.scalar(select(Transaction.first_seen_at).limit(1)) == first_seen
        assert session.scalar(select(func.count()).select_from(SyncExecution)) == 2


def test_pending_updates_and_links_to_new_statement(engine, fake_client):
    synchronize(engine, fake_client, "item")
    tx = fake_client.snapshot["transactions"]["card"][0]
    tx["status"] = "POSTED"
    tx["creditCardMetadata"]["billId"] = "bill"
    fake_client.snapshot["bills"]["card"] = [
        {
            "id": "bill",
            "dueDate": "2026-12-01T00:00:00Z",
            "totalAmount": Decimal("50.12"),
            "totalAmountCurrencyCode": "BRL",
            "payments": [
                {"paymentDate": "2026-12-01", "amount": Decimal("50.12"), "paymentMode": "DEBIT_ACCOUNT"}
            ],
        }
    ]
    synchronize(engine, fake_client, "item")
    with Session(engine) as session:
        row = session.scalar(select(Transaction).where(Transaction.external_id == "card-tx"))
        assert row.status == "POSTED"
        assert row.statement_id == session.scalar(select(CardStatement.id))
        assert row.purchase_total_amount is None
        assert session.scalar(select(CardStatement.payments))[0]["amount"] == "50.12"


def test_validation_failure_rolls_back_all_financial_changes(engine, fake_client):
    synchronize(engine, fake_client, "item")
    fake_client.snapshot["accounts"][0]["balance"] = Decimal("999")
    fake_client.snapshot["transactions"]["card"][0]["status"] = "INVALID"
    with pytest.raises(SyncError, match="INVALID_PROVIDER_DATA"):
        synchronize(engine, fake_client, "item")
    with Session(engine) as session:
        assert session.scalar(select(Account.balance).where(Account.external_id == "bank")) == Decimal(
            "123.4567890123456789"
        )
        assert (
            session.scalar(select(Transaction.status).where(Transaction.external_id == "card-tx"))
            == "PENDING"
        )
        failed = session.scalar(select(SyncExecution).where(SyncExecution.status == "FAILED"))
        assert failed.error_code == "INVALID_PROVIDER_DATA"
        assert failed.finished_at is not None


def test_remote_page_failure_keeps_last_success(engine, fake_client):
    synchronize(engine, fake_client, "item")
    with Session(engine) as session:
        last_success = session.scalar(select(BankConnection.last_successful_sync_at))

    class BrokenClient:
        def fetch(self, item_id):
            raise SyncError("PLUGGY_HTTP_429")

    with pytest.raises(SyncError, match="PLUGGY_HTTP_429"):
        synchronize(engine, BrokenClient(), "item")
    with Session(engine) as session:
        assert session.scalar(select(BankConnection.last_successful_sync_at)) == last_success
        assert session.scalar(select(func.count()).select_from(Transaction)) == 2


def test_missing_transaction_does_not_delete_history(engine, fake_client):
    synchronize(engine, fake_client, "item")
    fake_client.snapshot["transactions"]["bank"] = []
    synchronize(engine, fake_client, "item")
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Transaction)) == 2


def test_concurrent_sync_rejected(engine, fake_client):
    key = int.from_bytes(hashlib.sha256(b"pluggy:item").digest()[:8], signed=True)
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
        with pytest.raises(SyncError, match="SYNC_ALREADY_RUNNING"):
            synchronize(engine, fake_client, "item")


def test_migration_downgrade_and_upgrade(engine):
    with engine.begin() as connection:
        config = Config("alembic.ini")
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        assert "accounts" not in inspect(connection).get_table_names()
        command.upgrade(config, "head")
        assert "accounts" in inspect(connection).get_table_names()


def test_interrupted_execution_is_recovered_on_next_sync(engine, fake_client):
    synchronize(engine, fake_client, "item")
    with Session(engine) as session, session.begin():
        connection_id = session.scalar(select(BankConnection.id))
        stale = SyncExecution(connection_id=connection_id, started_at=utcnow(), status="RUNNING", counts={})
        session.add(stale)
        session.flush()
        stale_id = stale.id
    synchronize(engine, fake_client, "item")
    with Session(engine) as session:
        stale = session.get(SyncExecution, stale_id)
        assert stale.status == "FAILED"
        assert stale.error_code == "INTERRUPTED"
        assert stale.finished_at is not None
