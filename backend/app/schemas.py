from datetime import date, datetime
from decimal import Decimal
from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class AccountRead(ReadModel):
    id: UUID
    connection_id: UUID
    type: str
    subtype: str | None
    name: str
    currency: str
    balance: Decimal | None
    balance_observed_at: datetime
    credit_limit: Decimal | None
    available_credit_limit: Decimal | None


class TransactionRead(ReadModel):
    id: UUID
    account_id: UUID
    description: str
    occurred_at: datetime
    raw_amount: Decimal
    direction: Literal["DEBIT", "CREDIT"]
    currency: str
    status: Literal["PENDING", "POSTED"]
    operation_type: str | None
    installment_number: int | None
    total_installments: int | None
    purchase_date: date | None
    purchase_total_amount: Decimal | None
    statement_id: UUID | None

    @computed_field
    @property
    def flow_amount(self) -> Decimal:
        return -abs(self.raw_amount) if self.direction == "DEBIT" else abs(self.raw_amount)

    @computed_field
    @property
    def is_statement_payment(self) -> bool:
        return self.operation_type == "PAGAMENTO_FATURA"


class StatementRead(ReadModel):
    id: UUID
    account_id: UUID
    due_date: date
    closing_date: date | None
    total_amount: Decimal
    currency: str
    minimum_payment: Decimal | None
    payments: list[dict]


class SyncRead(ReadModel):
    id: UUID
    connection_id: UUID
    started_at: datetime
    finished_at: datetime | None
    status: str
    counts: dict
    error_code: str | None


class ConnectionRead(ReadModel):
    id: UUID
    institution_name: str | None
    provider_status: str | None
    last_provider_update_at: datetime | None
    consent_expires_at: datetime | None
    last_successful_sync_at: datetime | None
    latest_execution: SyncRead | None = None
