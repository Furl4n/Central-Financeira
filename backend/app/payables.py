"""Estimated known card commitments, never a DDA lookup or a payment instruction."""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select

from app.models import Account, CardStatement, Transaction


def card_payables(session):
    # Each statement is included once; linked purchases must not be added again.
    totals = defaultdict(lambda: Decimal(0))
    statement_count = 0
    pending_count = 0
    accounts = list(session.scalars(select(Account).where(Account.type == "CREDIT")))
    for account in accounts:
        for statement in session.scalars(select(CardStatement).where(CardStatement.account_id == account.id)):
            paid = sum((Decimal(str(payment["amount"])) for payment in statement.payments), Decimal(0))
            remaining = max(statement.total_amount - paid, Decimal(0))
            if remaining > 0:
                totals[statement.currency] += remaining
                statement_count += 1
        # Keep refunds within the same account and currency; never offset another card's debt.
        unbilled = defaultdict(lambda: Decimal(0))
        for tx in session.scalars(
            select(Transaction).where(
                Transaction.account_id == account.id,
                Transaction.status == "PENDING",
                Transaction.statement_id.is_(None),
                Transaction.external_bill_id.is_(None),
            )
        ):
            if tx.operation_type == "PAGAMENTO_FATURA":
                continue  # Evidence of settlement is already in statement.payments.
            currency = tx.currency
            amount = tx.raw_amount
            if tx.currency != account.currency and tx.amount_in_account_currency is not None:
                currency = account.currency
                amount = tx.amount_in_account_currency
            unbilled[currency] += abs(amount) if tx.direction == "DEBIT" else -abs(amount)
            if tx.direction == "DEBIT":
                pending_count += 1
        for currency, amount in unbilled.items():
            totals[currency] += max(amount, Decimal(0))
    # Distinguish a known zero in a connected card's currency from missing card data.
    for account in accounts:
        totals[account.currency] += Decimal(0)
    return {
        "totals": [{"currency": currency, "amount": amount} for currency, amount in sorted(totals.items())],
        "statement_count": statement_count,
        "pending_purchase_count": pending_count,
        "boletos_available": False,
        "estimated": True,
    }
