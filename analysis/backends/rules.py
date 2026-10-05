"""Правиловая заглушка: «логистическая модель», веса в которой выставлены
вручную. probability = sigmoid(bias + Σ вкладов), а вклад каждого показателя
выражается в лог-шансах — ровно так, как читаются SHAP-значения линейной
модели. Поэтому формат ответа совпадает с форматом будущей ML-модели.

Веса — эвристика, НЕ обучены на данных; вероятности не калиброваны.
Не измеренный показатель вклада не даёт."""
import math
from dataclasses import dataclass
from typing import Callable

from analysis.anemia import hb_threshold
from analysis.backends import thresholds as T
from common.schemas import (KEY_FEATURES_MAX, Condition, ConditionPrediction,
                            DeidentifiedCase, FeatureContribution)

TOP_K = KEY_FEATURES_MAX
Band = tuple[Callable[[float], bool], float]


@dataclass(frozen=True)
class Ctx:
    case: DeidentifiedCase

    def lab(self, name: str) -> float | None:
        return getattr(self.case.labs, name)

    @property
    def hb_threshold(self) -> float:
        return hb_threshold(self.case.sex, self.case.pregnant)


@dataclass(frozen=True)
class Evidence:
    feature: str
    fn: Callable[[Ctx], float | None]   # вклад в лог-шансах; None = нет данных
    counts: bool = True                 # False — «ворота», не считаются свидетельством


@dataclass(frozen=True)
class ConditionRule:
    bias: float
    evidence: tuple[Evidence, ...]


def banded(feature: str, *bands: Band) -> Evidence:
    """Первый подходящий диапазон определяет вклад; иначе 0."""
    def fn(ctx: Ctx) -> float | None:
        x = ctx.lab(feature)
        if x is None:
            return None
        for ok, weight in bands:
            if ok(x):
                return weight
        return 0.0
    return Evidence(feature, fn)


def _not_anemic_gate(weight: float) -> Evidence:
    def fn(ctx: Ctx) -> float | None:
        hb = ctx.lab("hemoglobin")
        if hb is None:
            return None
        return weight if hb >= ctx.hb_threshold else 0.0
    return Evidence("hemoglobin", fn, counts=False)


RULES: dict[Condition, ConditionRule] = {
    Condition.iron_deficiency: ConditionRule(-2.0, (
        banded("ferritin", (lambda x: x < T.FERRITIN_ABSOLUTE, 4.0),
                           (lambda x: x < T.FERRITIN_LOW, 2.5),
                           (lambda x: x > T.FERRITIN_HIGH, -2.0)),
        banded("TSAT", (lambda x: x < T.TSAT_LOW, 1.5)),
        banded("Ret_He", (lambda x: x < T.RET_HE_LOW, 2.0)),
        banded("MCV", (lambda x: x < T.MCV_LOW, 1.0)),
        banded("TIBC", (lambda x: x > T.TIBC_HIGH, 1.0)),
    )),
    Condition.b12_deficiency: ConditionRule(-2.5, (
        banded("vitamin_B12", (lambda x: x < T.B12_DEFICIENT, 3.0),
                              (lambda x: x < T.B12_BORDERLINE, 1.5),
                              (lambda x: x >= T.B12_NORMAL, -2.0)),
        banded("active_B12", (lambda x: x < T.ACTIVE_B12_LOW, 2.5),
                             (lambda x: x >= T.ACTIVE_B12_OK, -1.5)),
        banded("MMA", (lambda x: x > T.MMA_HIGH, 2.5),
                      (lambda x: x <= T.MMA_NORMAL, -2.0)),
        banded("homocysteine", (lambda x: x > T.HOMOCYSTEINE_HIGH, 1.5)),
        banded("MCV", (lambda x: x > T.MCV_HIGH, 1.0)),
        banded("LDH", (lambda x: x > T.LDH_HIGH, 0.5)),
    )),
    Condition.folate_deficiency: ConditionRule(-2.5, (
        banded("folate", (lambda x: x < T.FOLATE_DEFICIENT, 3.5),
                         (lambda x: x < T.FOLATE_BORDERLINE, 1.0),
                         (lambda x: x >= T.FOLATE_BORDERLINE, -1.0)),
        banded("homocysteine", (lambda x: x > T.HOMOCYSTEINE_HIGH, 1.0)),
        banded("MCV", (lambda x: x > T.MCV_HIGH, 0.8)),
    )),
    Condition.b6_deficiency: ConditionRule(-3.0, (
        banded("vitamin_B6", (lambda x: x < T.B6_DEFICIENT, 4.0),
                             (lambda x: x < T.B6_BORDERLINE, 1.5),
                             (lambda x: x >= T.B6_BORDERLINE, -1.0)),
    )),
    Condition.copper_deficiency: ConditionRule(-3.0, (
        banded("copper", (lambda x: x < T.COPPER_LOW, 3.5),
                         (lambda x: x >= T.COPPER_LOW, -1.0)),
        banded("ceruloplasmin", (lambda x: x < T.CERULOPLASMIN_LOW, 3.0)),
        banded("WBC", (lambda x: x < T.WBC_LOW, 0.5)),
    )),
    Condition.inflammation_anemia: ConditionRule(-2.0, (
        _not_anemic_gate(-4.0),
        banded("CRP", (lambda x: x > T.CRP_HIGH, 1.5)),
        banded("ferritin", (lambda x: x > T.FERRITIN_HIGH, 1.5)),
        banded("TSAT", (lambda x: x < T.TSAT_LOW, 1.0)),
    )),
}

DEFICIENCIES = (Condition.iron_deficiency, Condition.b12_deficiency,
                Condition.folate_deficiency, Condition.b6_deficiency,
                Condition.copper_deficiency)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class RulesBackend:
    version = "rules-0.1-draft"
    used_features: tuple[str, ...] = tuple(dict.fromkeys(
        [e.feature for r in RULES.values() for e in r.evidence]
    ))

    def predict(self, case: DeidentifiedCase) -> dict[Condition, ConditionPrediction]:
        ctx = Ctx(case)
        preds: dict[Condition, ConditionPrediction] = {}
        for cond, rule in RULES.items():
            preds[cond] = self._score(ctx, rule)
        preds[Condition.mixed_deficiency] = self._mixed(preds)
        return preds

    @staticmethod
    def _score(ctx: Ctx, rule: ConditionRule) -> ConditionPrediction:
        total = rule.bias
        has_evidence = False
        contribs: list[FeatureContribution] = []
        for ev in rule.evidence:
            w = ev.fn(ctx)
            if w is None:
                continue
            has_evidence = has_evidence or ev.counts
            total += w
            if w != 0.0:
                contribs.append(FeatureContribution(
                    feature=ev.feature, value=ctx.lab(ev.feature),
                    contribution=round(w, 3)))
        contribs.sort(key=lambda c: abs(c.contribution), reverse=True)
        p = _sigmoid(total)
        return ConditionPrediction(
            probability=round(p, 4), positive=p >= 0.5,
            has_evidence=has_evidence, top_features=contribs[:TOP_K])

    @staticmethod
    def _mixed(preds: dict[Condition, ConditionPrediction]) -> ConditionPrediction:
        """P(≥2 дефицитов одновременно) в предположении независимости."""
        ps = [preds[c].probability for c in DEFICIENCIES]
        p_none = math.prod(1 - p for p in ps)
        p_one = sum(p * math.prod(1 - q for j, q in enumerate(ps) if j != i)
                    for i, p in enumerate(ps))
        n_pos = sum(preds[c].positive for c in DEFICIENCIES)
        n_ev = sum(preds[c].has_evidence for c in DEFICIENCIES)
        return ConditionPrediction(
            probability=round(max(0.0, 1 - p_none - p_one), 4),
            positive=n_pos >= 2, has_evidence=n_ev >= 2, top_features=[])
