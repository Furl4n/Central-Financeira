from alembic import context

from app.config import Settings
from app.db import make_engine
from app.models import Base

target_metadata = Base.metadata


if context.is_offline_mode():
    context.configure(
        url=Settings().database_url.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    context.configure(
        connection=context.config.attributes["connection"], target_metadata=target_metadata, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(Settings().database_url.get_secret_value())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
