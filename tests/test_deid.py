import json
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from common.labs import LAB_SPECS
from common.labs_model import Labs
from common.schemas import AnalysisResult, Condition, IdentifiedCase
from scripts.gen_labs_model import TARGET, render
from deid import main
from deid.config import DeidSettings
from deid.security import Crypto
from deid.service import Deidentifier
from deid.vault import Vault

XLSX = Path(__file__).parent / "data" / "deficiency_anemia_first100.xlsx"
KEY = "test-service-key"
PATIENT_ID = "MRN-123456"


@pytest.fixture
def env():
    enc_key = Fernet.generate_key().decode()
    settings = DeidSettings.model_validate(dict(
        vault_enc_key=enc_key, service_api_key=KEY, analysis_api_key="a-key",
        vault_db_url="sqlite:///:memory:",
    ))
    # in-memory SQLite: один connection pool на все потоки
    from sqlalchemy.pool import StaticPool
    vault = Vault.__new__(Vault)
    from sqlalchemy import create_engine
    from deid.vault import Base
    vault.engine = create_engine("sqlite://", poolclass=StaticPool,
                                 connect_args={"check_same_thread": False})
    Base.metadata.create_all(vault.engine)
    deid = Deidentifier(Crypto(enc_key), vault)
    return settings, deid, vault


def case_dict(**over: Any) -> dict[str, Any]:
    d: dict[str, Any] = dict(patient_id=PATIENT_ID, age_years=64, sex="M", labs={"hemoglobin": 105})
    d.update(over)
    return d


def fake_analysis(captured: list):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured.append(body)
        res = AnalysisResult.model_validate(dict(
            case_token=body["case_token"], model_version="stub",
            anemia_detected=True, hemoglobin_threshold=130,
            predictions={c.value: {"probability": 0.9, "positive": c is Condition.b12_deficiency,
                                   "top_features": []} for c in Condition},
            anemia_class="B12_deficiency_anemia", deficiency_cause="B12_deficiency"))
        return httpx.Response(200, content=res.model_dump_json())
    return handler


@pytest.fixture
def client(env):
    settings, deid, vault = env
    captured: list = []

    async def _client():
        async with httpx.AsyncClient(
            base_url="http://analysis", transport=httpx.MockTransport(fake_analysis(captured))
        ) as c:
            yield c

    main.app.dependency_overrides[main._settings] = lambda: settings
    main.app.dependency_overrides[main._deidentifier] = lambda: deid
    main.app.dependency_overrides[main.analysis_client] = _client
    yield TestClient(main.app), captured, vault, deid
    main.app.dependency_overrides.clear()


def test_no_identifiers_reach_analysis(client):
    c, captured, _, _ = client
    r = c.post("/v1/process", json=case_dict(), headers={"X-API-Key": KEY})
    assert r.status_code == 200, r.text
    sent = json.dumps(captured[0])
    assert PATIENT_ID not in sent
    assert set(captured[0]) == {"case_token", "age_years", "sex", "pregnant", "labs"}


def test_vault_stores_encrypted_and_decryptable(client):
    c, captured, vault, deid = client
    c.post("/v1/process", json=case_dict(), headers={"X-API-Key": KEY})
    rec = vault.get(captured[0]["case_token"])
    assert PATIENT_ID.encode() not in rec.patient_ref_enc
    assert deid.crypto.decrypt(rec.patient_ref_enc) == PATIENT_ID


def test_tokens_unique(client):
    c, captured, _, _ = client
    for _ in range(2):
        c.post("/v1/process", json=case_dict(), headers={"X-API-Key": KEY})
    assert captured[0]["case_token"] != captured[1]["case_token"]


def test_age_top_coded(client):
    c, captured, _, _ = client
    c.post("/v1/process", json=case_dict(age_years=93), headers={"X-API-Key": KEY})
    assert captured[0]["age_years"] == 90


def test_full_name_rejected_and_not_echoed(client):
    c, _, _, _ = client
    r = c.post("/v1/process", json=case_dict(full_name="Иванов Иван"),
               headers={"X-API-Key": KEY})
    assert r.status_code == 422
    assert "Иванов" not in r.text and PATIENT_ID not in r.text


def test_bad_value_not_echoed(client):
    c, _, _, _ = client
    r = c.post("/v1/process", json=case_dict(labs={"hemoglobin": 9999}),
               headers={"X-API-Key": KEY})
    assert r.status_code == 422 and "9999" not in r.text


def test_requires_service_key(client):
    c, _, _, _ = client
    assert c.post("/v1/process", json=case_dict(),
                  headers={"X-API-Key": "wrong"}).status_code == 401


def test_pregnant_male_rejected():
    with pytest.raises(ValueError):
        IdentifiedCase.model_validate(case_dict(pregnant=True))


def _dataset_records() -> list[dict[str, Any]]:
    df = pd.read_excel(XLSX)
    return df.astype(object).where(df.notna(), None).to_dict("records")


def test_dataset_columns_match_registry():
    df = pd.read_excel(XLSX)
    assert list(df.columns[3:38]) == list(LAB_SPECS)


def test_all_100_dataset_rows_validate():
    """Реальные данные команды проходят контракт; пустые ячейки → None."""
    recs = _dataset_records()
    assert len(recs) == 100
    for r in recs:
        IdentifiedCase.model_validate(dict(
            patient_id=r["patient_id"], age_years=r["age_years"], sex=r["sex"],
            labs={k: r[k] for k in LAB_SPECS},
        ))


def test_labs_model_in_sync():
    """common/labs_model.py сгенерирован из common/labs.py и не отстал от него."""
    assert TARGET.read_text(encoding="utf-8") == render(), \
        "Запустите: python -m scripts.gen_labs_model"
    assert list(Labs.model_fields) == list(LAB_SPECS)


def test_env_path_is_anchored_to_project():
    """.env ищется рядом с проектом, а не в текущей папке терминала."""
    from deid import config
    assert config.ENV_FILE.is_absolute()
    assert config.ENV_FILE == Path(__file__).resolve().parents[1] / ".env"
