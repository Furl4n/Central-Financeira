from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import make_engine
from app.models import Account, BankConnection, CardStatement, SyncExecution, Transaction
from app.schemas import AccountRead, ConnectionRead, Page, StatementRead, SyncRead, TransactionRead


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


DB = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


def paginated(session, statement, schema, limit, offset):
    total = session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    rows = session.scalars(statement.limit(limit).offset(offset)).all()
    return {
        "items": [schema.model_validate(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def create_app(engine=None):
    app = FastAPI(title="Central Financeira", version="0.1.0")
    app.state.engine = (
        engine if engine is not None else make_engine(Settings().database_url.get_secret_value())
    )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        return JSONResponse(status_code=503, content={"detail": "Banco de dados indisponível"})

    @app.get("/health")
    def health(session: DB):
        session.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.get("/accounts", response_model=Page[AccountRead])
    def accounts(
        session: DB,
        limit: Limit = 50,
        offset: Offset = 0,
        type: Literal["BANK", "CREDIT"] | None = None,
        connection_id: UUID | None = None,
    ):
        statement = select(Account).order_by(Account.id)
        if type:
            statement = statement.where(Account.type == type)
        if connection_id:
            statement = statement.where(Account.connection_id == connection_id)
        return paginated(session, statement, AccountRead, limit, offset)

    @app.get("/transactions", response_model=Page[TransactionRead])
    def transactions(
        session: DB,
        limit: Limit = 50,
        offset: Offset = 0,
        account_id: UUID | None = None,
        status: Literal["POSTED", "PENDING"] | None = None,
        direction: Literal["DEBIT", "CREDIT"] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        for value in (date_from, date_to):
            if value is not None and value.tzinfo is None:
                raise HTTPException(422, "Informe datas com fuso horário")
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "date_from deve ser anterior ou igual a date_to")
        statement = select(Transaction).order_by(Transaction.occurred_at.desc(), Transaction.id)
        for column, value in (
            (Transaction.account_id, account_id),
            (Transaction.status, status),
            (Transaction.direction, direction),
        ):
            if value is not None:
                statement = statement.where(column == value)
        if date_from:
            statement = statement.where(Transaction.occurred_at >= date_from)
        if date_to:
            statement = statement.where(Transaction.occurred_at <= date_to)
        return paginated(session, statement, TransactionRead, limit, offset)

    @app.get("/statements", response_model=Page[StatementRead])
    def statements(session: DB, limit: Limit = 50, offset: Offset = 0, account_id: UUID | None = None):
        statement = select(CardStatement).order_by(CardStatement.due_date.desc(), CardStatement.id)
        if account_id:
            statement = statement.where(CardStatement.account_id == account_id)
        return paginated(session, statement, StatementRead, limit, offset)

    @app.get("/sync-status", response_model=list[ConnectionRead])
    def sync_status(session: DB):
        result = []
        for connection in session.scalars(select(BankConnection).order_by(BankConnection.id)):
            value = ConnectionRead.model_validate(connection)
            latest = session.scalar(
                select(SyncExecution)
                .where(SyncExecution.connection_id == connection.id)
                .order_by(SyncExecution.started_at.desc(), SyncExecution.id)
                .limit(1)
            )
            if latest:
                value.latest_execution = SyncRead.model_validate(latest)
            result.append(value)
        return result

    return app
