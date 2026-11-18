from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Identity:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class BankConnection(Identity, Base):
    __tablename__ = "bank_connections"
    __table_args__ = (UniqueConstraint("provider", "external_id"),)

    provider: Mapped[str] = mapped_column(String(30))
    external_id: Mapped[str] = mapped_column(String(200))
    institution_name: Mapped[str | None]
    provider_status: Mapped[str | None]
    last_provider_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Account(Identity, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_id"),
        CheckConstraint("type IN ('BANK', 'CREDIT')", name="account_type"),
    )

    connection_id: Mapped[UUID] = mapped_column(ForeignKey("bank_connections.id"))
    external_id: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(20))
    subtype: Mapped[str | None]
    name: Mapped[str]
    currency: Mapped[str] = mapped_column(String(3))
    balance: Mapped[Decimal | None] = mapped_column(Numeric())
    balance_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric())
    available_credit_limit: Mapped[Decimal | None] = mapped_column(Numeric())


class CardStatement(Identity, Base):
    __tablename__ = "card_statements"
    __table_args__ = (UniqueConstraint("account_id", "external_id"),)

    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    external_id: Mapped[str] = mapped_column(String(200))
    due_date: Mapped[date]
    closing_date: Mapped[date | None]
    total_amount: Mapped[Decimal] = mapped_column(Numeric())
    currency: Mapped[str] = mapped_column(String(3))
    minimum_payment: Mapped[Decimal | None] = mapped_column(Numeric())
    payments: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"))


class Transaction(Identity, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("account_id", "external_id"),
        CheckConstraint("direction IN ('DEBIT', 'CREDIT')", name="transaction_direction"),
        CheckConstraint("status IN ('PENDING', 'POSTED')", name="transaction_status"),
        Index("ix_transactions_date_id", "occurred_at", "id"),
        Index("ix_transactions_account_date", "account_id", "occurred_at"),
    )

    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    external_id: Mapped[str] = mapped_column(String(200))
    provider_id: Mapped[str | None]
    description: Mapped[str]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_date: Mapped[str]
    raw_amount: Mapped[Decimal] = mapped_column(Numeric())
    direction: Mapped[str] = mapped_column(String(10))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(10))
    operation_type: Mapped[str | None]
    provider_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    installment_number: Mapped[int | None]
    total_installments: Mapped[int | None]
    purchase_date: Mapped[date | None]
    purchase_total_amount: Mapped[Decimal | None] = mapped_column(Numeric())
    external_bill_id: Mapped[str | None]
    statement_id: Mapped[UUID | None] = mapped_column(ForeignKey("card_statements.id"))


class SyncExecution(Identity, Base):
    __tablename__ = "sync_executions"

    connection_id: Mapped[UUID] = mapped_column(ForeignKey("bank_connections.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20))
    counts: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    error_code: Mapped[str | None]
