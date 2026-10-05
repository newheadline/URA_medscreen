import secrets

from cryptography.fernet import Fernet


class Crypto:
    def __init__(self, vault_enc_key: str):
        self._fernet = Fernet(vault_enc_key.encode())

    @staticmethod
    def new_case_token() -> str:
        # Случайный, не выводится ни из каких данных пациента
        return "c_" + secrets.token_urlsafe(24)

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, token: bytes) -> str:
        return self._fernet.decrypt(token).decode()
