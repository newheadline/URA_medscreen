"""Защита идентифицирующих данных пациента (ФИО, ОМС, контакты).

Из ОДНОГО мастер-ключа (DATA_MASTER_KEY) через HKDF-SHA256 выводятся
независимые ключи под разные цели — их не нужно хранить по отдельности:
  • шифрование полей (Fernet);
  • HMAC для «слепого индекса» ОМС (уникальность и поиск без расшифровки);
  • HMAC цепочки журнала аудита.
Fernet — для прототипа; в боевой версии — сертифицированное СКЗИ (ГОСТ)."""
import base64
import hashlib
import hmac
import json
import re
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class KeyRing:
    def __init__(self, master_key: str):
        self._master = master_key.encode()

    def _derive(self, purpose: str) -> bytes:
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                    info=f"medscreen/v1/{purpose}".encode()).derive(self._master)

    def fernet_key(self) -> str:
        return base64.urlsafe_b64encode(self._derive("pii-encryption")).decode()

    def hmac_key(self, purpose: str) -> bytes:
        return self._derive(f"hmac/{purpose}")


class PiiCipher:
    def __init__(self, keyring: KeyRing):
        self._f = Fernet(keyring.fernet_key().encode())

    def enc_str(self, value: str) -> bytes:
        return self._f.encrypt(value.encode())

    def dec_str(self, blob: bytes) -> str:
        return self._f.decrypt(blob).decode()

    def enc_json(self, obj: Any) -> bytes:
        return self._f.encrypt(json.dumps(obj, ensure_ascii=False).encode())

    def dec_json(self, blob: bytes) -> Any:
        return json.loads(self._f.decrypt(blob))


# ───────── нормализация и «слепой индекс» ─────────
def normalize_oms(raw: str) -> str:
    """Убираем пробелы/дефисы, регистр — для сравнения и хеширования."""
    return re.sub(r"[\s\-]", "", raw).upper()


def oms_blind_index(keyring: KeyRing, oms_normalized: str) -> str:
    return hmac.new(keyring.hmac_key("oms-index"), oms_normalized.encode(),
                    hashlib.sha256).hexdigest()


def normalize_text(s: str) -> str:
    """Для поиска по ФИО: регистр, ё→е, лишние пробелы."""
    return " ".join(s.casefold().replace("ё", "е").split())
