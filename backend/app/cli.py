import sys

from app.config import Settings
from app.db import make_engine
from app.pluggy import PluggyClient, SyncError
from app.sync import synchronize


def main():
    try:
        settings = Settings()
        credentials = (
            settings.pluggy_client_id.get_secret_value(),
            settings.pluggy_client_secret.get_secret_value(),
            settings.pluggy_item_id.get_secret_value(),
        )
        if not all(value.strip() for value in credentials):
            print("Configure PLUGGY_CLIENT_ID, PLUGGY_CLIENT_SECRET e PLUGGY_ITEM_ID localmente.")
            return 2
        engine = make_engine(settings.database_url.get_secret_value())
        try:
            with PluggyClient(*credentials[:2]) as client:
                counts = synchronize(engine, client, credentials[2])
            print("Sincronização concluída:", counts)
        finally:
            engine.dispose()
    except SyncError as error:
        print("Sincronização interrompida:", error.code)
        return 1
    except Exception:
        print("Falha local. Verifique configuração, PostgreSQL e migrações; detalhes sensíveis omitidos.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
