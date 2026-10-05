from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    vault_enc_key: str
    deid_pepper: str
    service_api_key: str          # ключ, которым контур приёма вызывает обезличивание
    vault_db_url: str = "sqlite:///./vault.db"
    analysis_url: str = "http://localhost:8002"
    analysis_api_key: str = ""


def get_settings() -> Settings:
    return Settings()