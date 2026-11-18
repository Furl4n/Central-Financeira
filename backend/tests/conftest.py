import os
from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


@pytest.fixture
def engine():
    url = os.environ.get(
        "TEST_DATABASE_URL", "postgresql+psycopg://central:central_local@127.0.0.1:5433/central_financeira"
    )
    schema = "test_" + uuid4().hex
    admin = create_engine(url, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    test_engine = create_engine(
        url, connect_args={"options": f"-csearch_path={schema}"}, hide_parameters=True
    )
    try:
        with test_engine.begin() as connection:
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield test_engine
    finally:
        test_engine.dispose()
        # Only the fresh random test schema, never public or production tables.
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def snapshot():
    return {
        "item": {
            "status": "UPDATED",
            "connector": {"name": "Banco fictício"},
            "lastUpdatedAt": "2026-11-17T10:00:00Z",
            "consentExpiresAt": "2027-11-01T00:00:00Z",
        },
        "accounts": [
            {
                "id": "bank",
                "type": "BANK",
                "name": "Conta fictícia",
                "currencyCode": "BRL",
                "balance": Decimal("123.4567890123456789"),
            },
            {
                "id": "card",
                "type": "CREDIT",
                "name": "Cartão fictício",
                "currencyCode": "BRL",
                "balance": Decimal("50.12"),
                "creditData": {"creditLimit": Decimal("1000.00")},
            },
        ],
        "transactions": {
            "bank": [
                {
                    "id": "bank-tx",
                    "description": "Compra fictícia",
                    "date": "2026-11-10T12:00:00Z",
                    "amount": Decimal("-20.12"),
                    "type": "DEBIT",
                    "currencyCode": "BRL",
                    "status": "POSTED",
                }
            ],
            "card": [
                {
                    "id": "card-tx",
                    "description": "Parcela fictícia",
                    "date": "2026-11-11T12:00:00Z",
                    "amount": Decimal("50.12"),
                    "type": "DEBIT",
                    "currencyCode": "BRL",
                    "status": "PENDING",
                    "creditCardMetadata": {
                        "installmentNumber": 1,
                        "totalInstallments": 3,
                        "purchaseDate": "2026-11-11T00:00:00Z",
                    },
                }
            ],
        },
        "bills": {"bank": [], "card": []},
    }


class FakeClient:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def fetch(self, item_id):
        return deepcopy(self.snapshot)


@pytest.fixture
def fake_client(snapshot):
    return FakeClient(snapshot)
