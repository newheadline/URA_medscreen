import ast
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from analysis import main as amain
from analysis.anemia import hb_threshold
from analysis.backends.rules import RulesBackend
from analysis.config import ENV_FILE, AnalysisSettings
from analysis.classification import classify
from analysis.explain import build_key_features
from analysis.features import FEATURE_ORDER, case_to_row
from analysis.service import Analyzer
from common.labs import LAB_SPECS
from common.schemas import (KEY_FEATURES_MAX, KEY_FEATURES_MIN, AnemiaClass,
                            Condition, ConditionPrediction, DeficiencyCause,
                            DeidentifiedCase, FeatureContribution, Sex)

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "tests" / "data" / "deficiency_anemia_first100.xlsx"
KEY = "analysis-test-key"


def mk(sex: str = "F", age: int = 40, pregnant: bool | None = None,
       **labs: float) -> DeidentifiedCase:
    labs.setdefault("hemoglobin", 140.0)
    return DeidentifiedCase.model_validate(dict(
        case_token="c_test", age_years=age, sex=sex, pregnant=pregnant, labs=labs))


def mk_labs(labs: dict[str, float]) -> DeidentifiedCase:
    return DeidentifiedCase.model_validate(dict(
        case_token="c_test", age_years=40, sex="F", labs=labs))


analyzer = Analyzer(RulesBackend())


# ───────── уровень 1: анемия — жёсткое правило ─────────
@pytest.mark.parametrize("sex,preg,hb,expected", [
    ("M", None, 129.9, True), ("M", None, 130.0, False),
    ("F", None, 119.9, True), ("F", None, 120.0, False),
    ("F", True, 109.9, True), ("F", True, 110.0, False),
])
def test_anemia_who_thresholds(sex, preg, hb, expected):
    r = analyzer.analyze(mk(sex=sex, pregnant=preg, hemoglobin=hb))
    assert r.anemia_detected is expected
    assert r.hemoglobin_threshold == hb_threshold(Sex(sex), preg)


def test_anemia_is_not_a_model_output():
    assert "anemia" not in {c.value for c in Condition}
    r = analyzer.analyze(mk(hemoglobin=100))
    assert set(r.predictions) == set(Condition)


# ───────── уровень 2: классификация ─────────
def _preds(positive: set[Condition]) -> dict[Condition, ConditionPrediction]:
    return {c: ConditionPrediction(probability=0.9 if c in positive else 0.1,
                                   positive=c in positive) for c in Condition}


I, B, F = Condition.iron_deficiency, Condition.b12_deficiency, Condition.folate_deficiency
B6, CU = Condition.b6_deficiency, Condition.copper_deficiency
INF, MIX = Condition.inflammation_anemia, Condition.mixed_deficiency

# (анемия?, положительные флаги) → (anemia_class, deficiency_cause)
TABLE = [
    (True,  {B},        "B12_deficiency_anemia",       "B12_deficiency"),
    (False, {B},        "B12_deficiency_no_anemia",    "B12_deficiency"),
    (True,  {F},        "folate_deficiency_anemia",    "folate_deficiency"),
    (False, {F},        "folate_deficiency_no_anemia", "folate_deficiency"),
    (True,  {I},        "iron_deficiency_anemia",      "iron_deficiency"),
    (False, {I},        "latent_deficiency",           "iron_deficiency"),
    (True,  {B6},       "B6_deficiency",               "B6_deficiency"),
    (False, {B6},       "B6_deficiency",               "B6_deficiency"),
    (True,  {CU},       "copper_deficiency",           "copper_deficiency"),
    (False, {CU},       "copper_deficiency",           "copper_deficiency"),
    (True,  {INF},      "inflammation_anemia",         "inflammation"),
    (False, {INF},      "no_anemia_no_deficiency",     "none"),
    (True,  {I, B},     "mixed_deficiency",            "iron_B12"),
    (True,  {I, F},     "mixed_deficiency",            "iron_folate"),
    (False, {B, F},     "mixed_deficiency",            "B12_folate"),
    (True,  {B, B6},    "mixed_deficiency",            "undetermined"),   # пары нет в словаре
    (True,  {I, B, F},  "mixed_deficiency",            "undetermined"),
    (True,  set(),      "anemia_other",                "undetermined"),
    (False, set(),      "no_anemia_no_deficiency",     "none"),
]


@pytest.mark.parametrize("anemic,flags,cls,cause", TABLE)
def test_classification_table(anemic, flags, cls, cause):
    v = classify(anemic, _preds(flags))
    assert (v.anemia_class.value, v.cause.value) == (cls, cause)


def test_every_dataset_label_is_reachable():
    """Каждое значение из словарей датасета достижимо — иначе класс «мёртвый»."""
    got = [classify(a, _preds(f)) for a, f, *_ in TABLE]
    assert {v.anemia_class for v in got} == set(AnemiaClass)
    assert {v.cause for v in got} == set(DeficiencyCause)


def test_inflammation_markers_without_anemia_do_not_trigger():
    r = analyzer.analyze(mk(hemoglobin=145, CRP=20, ferritin=250, TSAT=15))
    assert not r.predictions[INF].positive
    assert r.anemia_class == AnemiaClass.no_anemia_no_deficiency


def test_b12_end_to_end_rules():
    r = analyzer.analyze(mk(hemoglobin=100, vitamin_B12=150, MMA=0.9))
    assert (r.anemia_class, r.deficiency_cause) == (
        AnemiaClass.b12_anemia, DeficiencyCause.b12)
    r = analyzer.analyze(mk(hemoglobin=140, vitamin_B12=150, MMA=0.9))   # латентный
    assert r.anemia_class == AnemiaClass.b12_no_anemia and not r.anemia_detected


def test_no_key_markers_means_no_evidence():
    r = analyzer.analyze(mk(hemoglobin=100))
    for c in Condition:
        assert r.predictions[c].has_evidence is False
        assert r.predictions[c].positive is False
    assert (r.anemia_class, r.deficiency_cause) == (
        AnemiaClass.anemia_other, DeficiencyCause.undetermined)
    assert r.key_features == []
    assert "ferritin" in r.missing_features and "hemoglobin" not in r.missing_features


def test_inflammation_anemia_end_to_end():
    r = analyzer.analyze(mk(hemoglobin=100, CRP=20, ferritin=250, TSAT=15))
    assert (r.anemia_class, r.deficiency_cause) == (
        AnemiaClass.inflammation_anemia, DeficiencyCause.inflammation)
    assert not r.predictions[I].positive


def test_measured_feature_not_reported_missing():
    assert "ferritin" not in analyzer.analyze(mk(ferritin=50)).missing_features


# ───────── 5–7 ключевых признаков ─────────
RICH_B12: dict[str, float] = dict(hemoglobin=95, vitamin_B12=150, active_B12=15, MMA=0.9,
                homocysteine=30, MCV=108, LDH=400)


def test_key_features_5_to_7_sorted_and_normalised():
    r = analyzer.analyze(mk_labs(RICH_B12))
    kf = r.key_features
    assert KEY_FEATURES_MIN <= len(kf) <= KEY_FEATURES_MAX
    assert [k.importance for k in kf] == sorted((k.importance for k in kf), reverse=True)
    assert sum(k.importance for k in kf) == pytest.approx(1.0, abs=1e-3)
    assert {k.feature for k in kf} <= set(RICH_B12)
    assert all(k.direction == "supports" for k in kf)
    top = kf[0]
    assert top.label and top.unit and top.value is not None


def test_key_features_capped_at_seven():
    r = analyzer.analyze(mk_labs(RICH_B12))
    preds = dict(r.predictions)
    many = [FeatureContribution(feature=f, value=1.0, contribution=1.0 + i / 10)
            for i, f in enumerate(list(LAB_SPECS)[:12])]
    preds[B] = ConditionPrediction(probability=0.9, positive=True, top_features=many)
    assert len(build_key_features(preds, (B,))) == KEY_FEATURES_MAX


def test_key_features_not_padded_when_data_is_scarce():
    """Заглушка по B6 знает один показатель: 1 признак, а не 5 нулей."""
    r = analyzer.analyze(mk(hemoglobin=100, vitamin_B6=10))
    assert r.deficiency_cause == DeficiencyCause.b6
    assert [k.feature for k in r.key_features] == ["vitamin_B6"]


def test_key_features_merge_for_mixed_deficiency():
    r = analyzer.analyze(mk(hemoglobin=100, ferritin=8, TSAT=10,
                            vitamin_B12=150, MMA=1.0))
    assert r.deficiency_cause == DeficiencyCause.iron_b12
    feats = {k.feature for k in r.key_features}
    assert {"ferritin", "vitamin_B12"} <= feats        # вклады обоих дефицитов


def test_no_cause_no_key_features():
    assert analyzer.analyze(mk(hemoglobin=145)).key_features == []


def test_result_shape():
    r = analyzer.analyze(mk(hemoglobin=100, ferritin=8))
    assert set(r.predictions) == set(Condition)
    for pred in r.predictions.values():
        assert 0 <= pred.probability <= 1
        mags = [abs(f.contribution) for f in pred.top_features]
        assert mags == sorted(mags, reverse=True)
    assert r.case_token == "c_test" and r.model_version.startswith("rules-")


def test_feature_contract_matches_dataset_columns():
    cols = list(pd.read_excel(XLSX).columns)
    assert FEATURE_ORDER == cols[1:38]          # age_years, sex, 35 показателей
    assert list(case_to_row(mk())) == FEATURE_ORDER


def test_dataset_sanity():
    """Заглушка на реальных данных: анемия совпадает с разметкой на 100 %,
    B12 ловится в большинстве случаев. Жёстких метрик нет — это не обученная
    модель, а 100 строк одного класса."""
    df = pd.read_excel(XLSX)
    recs = df.astype(object).where(df.notna(), None).to_dict("records")
    anemia_ok = b12_hit = label_ok = 0
    for i, r in enumerate(recs):
        case = DeidentifiedCase.model_validate(dict(
            case_token=f"c_{i}", age_years=min(r["age_years"], 90), sex=r["sex"],
            labs={k: r[k] for k in LAB_SPECS}))
        res = analyzer.analyze(case)
        anemia_ok += res.anemia_detected == bool(r["anemia"])
        b12_hit += res.predictions[B].positive
        label_ok += res.anemia_class.value == r["anemia_class"]
    assert anemia_ok == 100
    assert b12_hit >= 85
    assert label_ok >= 75


# ───────── API ─────────
@pytest.fixture
def client():
    s = AnalysisSettings.model_validate({"analysis_api_key": KEY})
    amain.app.dependency_overrides[amain._settings] = lambda: s
    amain.app.dependency_overrides[amain._analyzer] = lambda: analyzer
    yield TestClient(amain.app)
    amain.app.dependency_overrides.clear()


def body(**over: Any) -> dict[str, Any]:
    d: dict[str, Any] = dict(case_token="c_api", age_years=50, sex="F",
                             labs={"hemoglobin": 100, "vitamin_B12": 150, "MMA": 0.9})
    d.update(over)
    return d


def test_api_ok(client):
    r = client.post("/v1/analyze", json=body(), headers={"X-API-Key": KEY})
    assert r.status_code == 200, r.text
    assert r.json()["case_token"] == "c_api"
    assert r.json()["anemia_class"] == "B12_deficiency_anemia"


def test_api_requires_key(client):
    assert client.post("/v1/analyze", json=body(),
                       headers={"X-API-Key": "nope"}).status_code == 401
    assert client.post("/v1/analyze", json=body()).status_code == 422


def test_api_rejects_identifiers(client):
    """Контур анализа физически не принимает идентифицирующие поля."""
    r = client.post("/v1/analyze", json=body(patient_id="MRN-1"), headers={"X-API-Key": KEY})
    assert r.status_code == 422 and "MRN-1" not in r.text


def test_api_rejects_minors_without_echo(client):
    r = client.post("/v1/analyze", json=body(age_years=9), headers={"X-API-Key": KEY})
    assert r.status_code == 422


def test_health(client):
    assert client.get("/health").json()["model_version"].startswith("rules-")


# ───────── изоляция контура ─────────
def test_analysis_isolation():
    """Контур анализа не импортирует ни обезличивание, ни хранилище, ни
    конфиг с ключами, и не знает про идентифицированную схему."""
    forbidden_modules = ("deid", "common.config", "sqlalchemy", "cryptography")
    for path in (ROOT / "analysis").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            for n in names:
                assert not n.startswith(forbidden_modules), f"{path.name}: import {n}"
            if isinstance(node, ast.Name):
                assert node.id != "IdentifiedCase", f"{path.name}: uses IdentifiedCase"


def test_analysis_env_is_separate_from_deid():
    from deid import config as deid_config
    assert ENV_FILE.parent == ROOT / "analysis"
    assert ENV_FILE != deid_config.ENV_FILE
