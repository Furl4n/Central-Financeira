from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings


def make_engine(url: str):
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)


def session_factory(settings: Settings):
    return sessionmaker(make_engine(settings.database_url.get_secret_value()), expire_on_commit=False)
