"""Гистограмма «что повлияло на вывод»: 5–7 признаков с весами."""
from typing import Sequence

from common.labs import LAB_SPECS
from common.schemas import (KEY_FEATURES_MAX, Condition, ConditionPrediction,
                            KeyFeature)

_EXTRA = {"age_years": ("Возраст", "лет"), "sex": ("Пол", "")}


def _label(feature: str) -> tuple[str, str]:
    if feature in LAB_SPECS:
        s = LAB_SPECS[feature]
        return s.desc, s.unit
    return _EXTRA.get(feature, (feature, ""))


def build_key_features(
    preds: dict[Condition, ConditionPrediction],
    implicated: Sequence[Condition],
) -> list[KeyFeature]:
    """Складывает вклады признаков по условиям, объясняющим вывод (для
    смешанного дефицита — по обоим), берёт до KEY_FEATURES_MAX крупнейших
    по модулю. Если значимых признаков меньше — возвращает сколько есть."""
    total: dict[str, float] = {}
    values: dict[str, float | str | None] = {}
    for cond in implicated:
        for f in preds[cond].top_features:
            total[f.feature] = total.get(f.feature, 0.0) + f.contribution
            values.setdefault(f.feature, f.value)

    ranked = sorted(((k, v) for k, v in total.items() if v != 0.0),
                    key=lambda kv: abs(kv[1]), reverse=True)[:KEY_FEATURES_MAX]
    norm = sum(abs(v) for _, v in ranked)
    out: list[KeyFeature] = []
    for feature, contribution in ranked:
        label, unit = _label(feature)
        out.append(KeyFeature(
            feature=feature, label=label, unit=unit, value=values[feature],
            contribution=round(contribution, 3),
            importance=round(abs(contribution) / norm, 4),
            direction="supports" if contribution > 0 else "opposes"))
    return out
