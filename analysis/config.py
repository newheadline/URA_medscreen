"""Конфиг ТОЛЬКО контура анализа. Свой .env (analysis/.env): здесь нет ни
ключа шифрования хранилища, ни строки подключения к БД соответствий."""
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent / ".env"


class AnalysisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    analysis_api_key: SecretStr      # тот же, что ANALYSIS_API_KEY в .env обезличивания
    model_backend: str = "rules"     # "rules" — правиловая заглушка; позже "ml"
