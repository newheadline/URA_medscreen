from analysis.anemia import hb_threshold, is_anemic
from analysis.backends.base import ModelBackend
from analysis.classification import classify
from analysis.explain import build_key_features
from common.schemas import AnalysisResult, DeidentifiedCase


class Analyzer:
    def __init__(self, backend: ModelBackend):
        self.backend = backend

    def analyze(self, case: DeidentifiedCase) -> AnalysisResult:
        # Уровень 1: анемия — правило, модель не участвует
        hb = case.labs.hemoglobin
        anemic = is_anemic(hb, case.sex, case.pregnant)

        # Уровень 2: дефициты — модель
        preds = self.backend.predict(case)
        verdict = classify(anemic, preds)
        DEMOGRAPHIC = {"age_years", "sex"}   # живут в DeidentifiedCase, не в labs
        missing = [f for f in self.backend.used_features
                   if f not in DEMOGRAPHIC and getattr(case.labs, f, None) is None]
        return AnalysisResult(
            case_token=case.case_token,
            model_version=self.backend.version,
            anemia_detected=anemic,
            hemoglobin_threshold=hb_threshold(case.sex, case.pregnant),
            predictions=preds,
            anemia_class=verdict.anemia_class,
            deficiency_cause=verdict.cause,
            key_features=build_key_features(preds, verdict.implicated),
            missing_features=missing,
        )
