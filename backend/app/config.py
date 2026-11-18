from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://central:central_local@127.0.0.1:5433/central_financeira"
    )
    pluggy_client_id: SecretStr = SecretStr("")
    pluggy_client_secret: SecretStr = SecretStr("")
    pluggy_item_id: SecretStr = SecretStr("")
