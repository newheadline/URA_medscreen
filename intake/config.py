from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parent / ".env"


class IntakeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore",
    )

    database_url: str
    deid_url: str = "http://localhost:8001"
    deid_api_key: SecretStr
    # Один мастер-ключ → HKDF → ключи шифрования ФИО/ОМС/контактов, слепого индекса ОМС
    # и HMAC журнала аудита. Сгенерировать: python -c "import secrets; print(secrets.token_urlsafe(48))"
    # ПОТЕРЯ КЛЮЧА = ФИО/ОМС/контакты не расшифровать; СМЕНА КЛЮЧА без перешифровки то же самое.
    data_master_key: SecretStr
    cors_origins: str = ""              # через запятую; пусто — CORS выключен
    worker_poll_seconds: float = 1.0
    worker_stale_seconds: int = 900
    jwt_secret: SecretStr              # подпись токенов; сгенерировать: python -c "import secrets; print(secrets.token_urlsafe(48))"
    jwt_ttl_hours: int = 720           # 30 дней — хватит на демо
    demo_login_enabled: bool = True    # выключить в проде


    @field_validator("data_master_key")
    @classmethod
    def _long_key(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("DATA_MASTER_KEY must be at least 32 characters")
        return v

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
