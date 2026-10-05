"""Сквозная цепочка: приём → обезличивание → анализ (в одном процессе)."""
import httpx
import pytest
from fastapi.testclient import TestClient

from analysis import main as amain
from analysis.backends.rules import RulesBackend
from analysis.config import AnalysisSettings
from analysis.service import Analyzer
from common.schemas import Condition, DeidentifiedCase
from deid import main as dmain
from tests.test_deid import KEY, PATIENT_ID, env  # noqa: F401  (fixture)

ANALYSIS_KEY = "shared-analysis-key"


class SpyBackend(RulesBackend):
    seen: list[str] = []

    def predict(self, case: DeidentifiedCase):
        SpyBackend.seen.append(case.model_dump_json())
        return super().predict(case)


@pytest.fixture
def stack(env):  # noqa: F811
    settings, deid, vault = env
    SpyBackend.seen = []
    a_settings = AnalysisSettings.model_validate({"analysis_api_key": ANALYSIS_KEY})
    amain.app.dependency_overrides[amain._settings] = lambda: a_settings
    amain.app.dependency_overrides[amain._analyzer] = lambda: Analyzer(SpyBackend())

    async def _client():
        async with httpx.AsyncClient(
            base_url="http://analysis",
            transport=httpx.ASGITransport(app=amain.app),
            headers={"X-API-Key": ANALYSIS_KEY},
        ) as c:
            yield c

    dmain.app.dependency_overrides[dmain._settings] = lambda: settings
    dmain.app.dependency_overrides[dmain._deidentifier] = lambda: deid
    dmain.app.dependency_overrides[dmain.analysis_client] = _client
    yield TestClient(dmain.app), vault
    dmain.app.dependency_overrides.clear()
    amain.app.dependency_overrides.clear()


def test_full_chain(stack):
    client, vault = stack
    r = client.post("/v1/process", headers={"X-API-Key": KEY}, json=dict(
        patient_id=PATIENT_ID, age_years=64, sex="M",
        labs={"hemoglobin": 105, "vitamin_B12": 150, "MMA": 0.9}))
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["anemia_detected"] is True and out["hemoglobin_threshold"] == 130
    assert (out["anemia_class"], out["deficiency_cause"]) == ("B12_deficiency_anemia", "B12_deficiency")
    assert 1 <= len(out["key_features"]) <= 7
    assert set(out["predictions"]) == {c.value for c in Condition}
    assert vault.get(out["case_token"]) is not None
    # анализ видел только обезличенный набор
    assert len(SpyBackend.seen) == 1 and PATIENT_ID not in SpyBackend.seen[0]


def test_minor_rejected_before_vault(stack):
    client, vault = stack
    r = client.post("/v1/process", headers={"X-API-Key": KEY}, json=dict(
        patient_id=PATIENT_ID, age_years=12, sex="F", labs={"hemoglobin": 105}))
    assert r.status_code == 422 and SpyBackend.seen == []
