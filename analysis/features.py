"""Контракт признаков для ML-модели: порядок и имена = столбцы датасета.
Модель получает age_years, sex и 35 лабораторных показателей; пропуски = None
(для CatBoost/LightGBM → NaN)."""
from common.labs import LAB_SPECS
from common.schemas import DeidentifiedCase

FEATURE_ORDER: list[str] = ["age_years", "sex", *LAB_SPECS]


def case_to_row(case: DeidentifiedCase) -> dict[str, float | int | str | None]:
    row: dict[str, float | int | str | None] = {
        "age_years": case.age_years,
        "sex": case.sex.value,
    }
    for name in LAB_SPECS:
        row[name] = getattr(case.labs, name)
    return {k: row[k] for k in FEATURE_ORDER}
