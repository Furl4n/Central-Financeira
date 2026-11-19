from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


def date_only(value):
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    return value


class CreditData(ProviderModel):
    credit_limit: Decimal | None = Field(None, alias="creditLimit")
    available_credit_limit: Decimal | None = Field(None, alias="availableCreditLimit")


class ProviderAccount(ProviderModel):
    id: str = Field(min_length=1)
    type: Literal["BANK", "CREDIT"]
    subtype: str | None = None
    name: str
    currency: str = Field(alias="currencyCode", min_length=3, max_length=3)
    balance: Decimal | None = None
    credit_data: CreditData | None = Field(None, alias="creditData")


class CardMetadata(ProviderModel):
    installment_number: int | None = Field(None, alias="installmentNumber", ge=1)
    total_installments: int | None = Field(None, alias="totalInstallments", ge=1)
    purchase_date: date | None = Field(None, alias="purchaseDate")
    purchase_total_amount: Decimal | None = Field(None, alias="totalAmount")
    external_bill_id: str | None = Field(None, alias="billId")
    _date = field_validator("purchase_date", mode="before")(date_only)


class ProviderTransaction(ProviderModel):
    id: str = Field(min_length=1)
    provider_id: str | None = Field(None, alias="providerId")
    description: str
    date: str
    raw_amount: Decimal = Field(alias="amount")
    amount_in_account_currency: Decimal | None = Field(None, alias="amountInAccountCurrency")
    direction: Literal["DEBIT", "CREDIT"] = Field(alias="type")
    currency: str = Field(alias="currencyCode", min_length=3, max_length=3)
    status: Literal["PENDING", "POSTED"]
    operation_type: str | None = Field(None, alias="operationType")
    provider_created_at: datetime | None = Field(None, alias="createdAt")
    provider_updated_at: datetime | None = Field(None, alias="updatedAt")
    metadata: CardMetadata | None = Field(None, alias="creditCardMetadata")

    @field_validator("date")
    @classmethod
    def valid_date(cls, value):
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    def occurred_at(self):
        value = datetime.fromisoformat(self.date.replace("Z", "+00:00"))
        # Pluggy documents transaction dates as UTC. Preserve the source text too.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class StatementPayment(ProviderModel):
    payment_date: date = Field(alias="paymentDate")
    amount: Decimal
    payment_mode: str | None = Field(None, alias="paymentMode")
    value_type: str | None = Field(None, alias="valueType")
    _date = field_validator("payment_date", mode="before")(date_only)


class ProviderStatement(ProviderModel):
    id: str = Field(min_length=1)
    due_date: date = Field(alias="dueDate")
    closing_date: date | None = Field(None, alias="billClosingDate")
    total_amount: Decimal = Field(alias="totalAmount")
    currency: str = Field(alias="totalAmountCurrencyCode", min_length=3, max_length=3)
    minimum_payment: Decimal | None = Field(None, alias="minimumPaymentAmount")
    payments: list[StatementPayment] = Field(default_factory=list)
    _dates = field_validator("due_date", "closing_date", mode="before")(date_only)


class ProviderItem(ProviderModel):
    status: str
    last_updated_at: datetime | None = Field(None, alias="lastUpdatedAt")
    consent_expires_at: datetime | None = Field(None, alias="consentExpiresAt")
    connector: dict = Field(default_factory=dict)
