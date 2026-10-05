"""Конфиг ТОЛЬКО сервиса обезличивания. У контура анализа и контура приёма
свои .env: ключ шифрования хранилища никому, кроме этого сервиса, не нужен."""
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# .env ищем рядом с проектом (medscreen/.env), а не в текущей папке терминала
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class DeidSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    vault_enc_key: SecretStr        # ключ Fernet для шифрования patient_id в хранилище
    service_api_key: SecretStr      # ключ, который предъявляет контур приёма
    analysis_api_key: SecretStr     # ключ, который мы предъявляем контуру анализа
    vault_db_url: str               # postgresql+psycopg://user:pass@host:port/db
    analysis_url: str = "http://localhost:8002"
