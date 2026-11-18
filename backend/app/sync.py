import hashlib
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Account, BankConnection, CardStatement, SyncExecution, Transaction, utcnow
from app.pluggy import SyncError
from app.provider_schemas import ProviderAccount, ProviderItem, ProviderStatement, ProviderTransaction


def upsert(session, model, identity, values):
    row = session.scalar(select(model).filter_by(**identity))
    if row is None:
        row = model(**identity, **values)
        session.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    session.flush()
    return row


def apply_snapshot(session: Session, connection_id: UUID, snapshot: dict):
    now = utcnow()
    item = ProviderItem.model_validate(snapshot["item"])
    connection = session.get(BankConnection, connection_id)
    connection.provider_status = item.status
    connection.institution_name = item.connector.get("name")
    connection.last_provider_update_at = item.last_updated_at
    connection.consent_expires_at = item.consent_expires_at
    counts = {"accounts": 0, "transactions": 0, "statements": 0}
    for raw_account in snapshot["accounts"]:
        source = ProviderAccount.model_validate(raw_account)
        values = source.model_dump(exclude={"id", "credit_data"})
        values.update(balance_observed_at=now, credit_limit=None, available_credit_limit=None)
        if source.credit_data:
            values.update(source.credit_data.model_dump())
        account = upsert(session, Account, {"connection_id": connection_id, "external_id": source.id}, values)
        counts["accounts"] += 1
        for raw_statement in snapshot["bills"][source.id]:
            bill = ProviderStatement.model_validate(raw_statement)
            values = bill.model_dump(exclude={"id", "payments"})
            values["payments"] = [payment.model_dump(mode="json") for payment in bill.payments]
            upsert(session, CardStatement, {"account_id": account.id, "external_id": bill.id}, values)
            counts["statements"] += 1
        # Includes previously fetched statements, even if the source's window changed.
        statements = {
            bill.external_id: bill.id
            for bill in session.scalars(select(CardStatement).where(CardStatement.account_id == account.id))
        }
        for raw_transaction in snapshot["transactions"][source.id]:
            tx = ProviderTransaction.model_validate(raw_transaction)
            values = tx.model_dump(exclude={"id", "date", "metadata"})
            values.update(source_date=tx.date, occurred_at=tx.occurred_at(), last_seen_at=now)
            metadata = (
                tx.metadata.model_dump()
                if tx.metadata
                else {
                    "installment_number": None,
                    "total_installments": None,
                    "purchase_date": None,
                    "purchase_total_amount": None,
                    "external_bill_id": None,
                }
            )
            values.update(metadata, statement_id=statements.get(metadata["external_bill_id"]))
            upsert(session, Transaction, {"account_id": account.id, "external_id": tx.id}, values)
            counts["transactions"] += 1
        # Reconcile references on older transactions if their bill arrived later.
        for tx in session.scalars(select(Transaction).where(Transaction.account_id == account.id)):
            if tx.external_bill_id in statements:
                tx.statement_id = statements[tx.external_bill_id]
    connection.last_successful_sync_at = now
    return counts


def synchronize(engine, client, item_id: str):
    # Transaction-level PostgreSQL lock held on a dedicated connection during fetch and commit.
    lock_key = int.from_bytes(hashlib.sha256(("pluggy:" + item_id).encode()).digest()[:8], signed=True)
    with engine.begin() as lock:
        if not lock.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_key}):
            raise SyncError("SYNC_ALREADY_RUNNING")
        with Session(engine) as session, session.begin():
            connection = upsert(session, BankConnection, {"provider": "pluggy", "external_id": item_id}, {})
            connection_id = connection.id
            # We own the lock: previous RUNNING entries can only be interrupted processes.
            for stale in session.scalars(
                select(SyncExecution).where(
                    SyncExecution.connection_id == connection_id, SyncExecution.status == "RUNNING"
                )
            ):
                stale.status = "FAILED"
                stale.error_code = "INTERRUPTED"
                stale.finished_at = utcnow()
            execution = SyncExecution(
                connection_id=connection_id, started_at=utcnow(), status="RUNNING", counts={}
            )
            session.add(execution)
            session.flush()
            execution_id = execution.id
        try:
            snapshot = client.fetch(item_id)
            with Session(engine) as session, session.begin():
                counts = apply_snapshot(session, connection_id, snapshot)
                execution = session.get(SyncExecution, execution_id)
                execution.status = "SUCCEEDED"
                execution.counts = counts
                execution.finished_at = utcnow()
        except Exception as error:
            code = (
                error.code
                if isinstance(error, SyncError)
                else (
                    "INVALID_PROVIDER_DATA"
                    if isinstance(error, (ValidationError, ValueError, KeyError))
                    else "SYNC_FAILED"
                )
            )
            with Session(engine) as session, session.begin():
                execution = session.get(SyncExecution, execution_id)
                execution.status = "FAILED"
                execution.error_code = code
                execution.finished_at = utcnow()
            raise SyncError(code) from None
    return counts
