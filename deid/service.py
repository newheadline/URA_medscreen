from common.schemas import DeidentifiedCase, IdentifiedCase
from deid.security import Crypto
from deid.vault import Vault

AGE_TOP_CODE = 90   # возраст ≥90 — редкий квазиидентификатор, округляем вниз


class Deidentifier:
    def __init__(self, crypto: Crypto, vault: Vault):
        self.crypto = crypto
        self.vault = vault

    def run(self, case: IdentifiedCase) -> DeidentifiedCase:
        token = self.crypto.new_case_token()

        # Связь токен ↔ пациент — только в изолированном хранилище, шифрованно
        self.vault.put(token, self.crypto.encrypt(case.patient_id))

        # В выход попадают ТОЛЬКО перечисленные поля; patient_id не передаётся.
        return DeidentifiedCase(
            case_token=token,
            age_years=min(case.age_years, AGE_TOP_CODE),
            sex=case.sex,
            pregnant=case.pregnant,
            labs=case.labs,
        )
