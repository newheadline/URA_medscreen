"""Контракты между контурами. Что описано в DeidentifiedCase — то и может
попасть в контур анализа. Всё остальное отбрасывается/запрещается."""
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from common.labs_model import Labs


# Модель и референсы рассчитаны на взрослых (в датасете 18–93). Детские
# референсы Hb/MCV другие, поэтому такие случаи отклоняются на входе.
MIN_AGE_YEARS = 18


class Sex(str, Enum):
    male = "M"
    female = "F"


# ───────── Контур приёма → обезличивание (идентифицируемые данные) ─────────
class IdentifiedCase(BaseModel):
    """ФИО сюда НЕ передаётся (extra=forbid): модулю обезличивания оно не
    нужно, ФИО остаётся только в контуре приёма. Принцип минимизации."""
    model_config = ConfigDict(extra="forbid")

    patient_id: str = Field(min_length=1, max_length=64)   # МИС-id / номер карты
    age_years: int = Field(ge=MIN_AGE_YEARS, le=120)
    sex: Sex
    pregnant: bool | None = None
    labs: Labs

    @model_validator(mode="after")
    def _pregnancy_only_female(self):
        if self.pregnant and self.sex != Sex.female:
            raise ValueError("pregnant=true is only valid for sex=F")
        return self


# ───────── Обезличивание → анализ (то, что можно показывать ML) ─────────
class DeidentifiedCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_token: str                    # случайный токен этого анализа
    age_years: int = Field(ge=MIN_AGE_YEARS)   # top-coding: всё ≥90 → 90
    sex: Sex
    pregnant: bool | None = None
    labs: Labs


# ───────── Анализ → обратно ─────────
# Сколько признаков показывать в «объяснении» итогового вывода (гистограмма).
# Меньше KEY_FEATURES_MIN возможно, только если значимых признаков нет:
# нулями не добиваем.
KEY_FEATURES_MIN = 5
KEY_FEATURES_MAX = 7


class Condition(str, Enum):
    """Бинарные цели, которые предсказывает МОДЕЛЬ. Анемия сюда не входит:
    это жёсткое правило по гемоглобину и полу (analysis/anemia.py)."""
    iron_deficiency = "iron_deficiency"
    b12_deficiency = "B12_deficiency"
    folate_deficiency = "folate_deficiency"
    b6_deficiency = "B6_deficiency"
    copper_deficiency = "copper_deficiency"
    inflammation_anemia = "inflammation_anemia"
    mixed_deficiency = "mixed_deficiency"


class AnemiaClass(str, Enum):
    """Значения anemia_class из датасета (12 штук)."""
    b12_anemia = "B12_deficiency_anemia"
    b12_no_anemia = "B12_deficiency_no_anemia"
    b6 = "B6_deficiency"
    copper = "copper_deficiency"
    folate_anemia = "folate_deficiency_anemia"
    folate_no_anemia = "folate_deficiency_no_anemia"
    inflammation_anemia = "inflammation_anemia"
    iron_anemia = "iron_deficiency_anemia"
    latent = "latent_deficiency"
    mixed = "mixed_deficiency"
    no_anemia_no_deficiency = "no_anemia_no_deficiency"
    anemia_other = "anemia_other"


class DeficiencyCause(str, Enum):
    """Значения deficiency_cause из датасета (11 штук)."""
    b12 = "B12_deficiency"
    b12_folate = "B12_folate"
    b6 = "B6_deficiency"
    copper = "copper_deficiency"
    folate = "folate_deficiency"
    inflammation = "inflammation"
    iron_b12 = "iron_B12"
    iron = "iron_deficiency"
    iron_folate = "iron_folate"
    none = "none"                    # дефицита нет
    undetermined = "undetermined"    # анемия есть, причина не установлена


class FeatureContribution(BaseModel):
    feature: str                       # имя из LAB_SPECS либо age_years / sex
    value: float | str | None          # значение признака (None = не измерен)
    contribution: float                # вклад (SHAP) в лог-шансы этого класса;
                                       # >0 повышает вероятность, <0 понижает


class KeyFeature(BaseModel):
    """Одна строка гистограммы «что повлияло на вывод»."""
    feature: str
    label: str                         # русское название для интерфейса
    unit: str
    value: float | str | None
    contribution: float                # со знаком, в лог-шансах
    importance: float = Field(ge=0, le=1)   # доля |вклада| среди показанных; Σ = 1
    direction: Literal["supports", "opposes"]   # за вывод / против вывода


class ConditionPrediction(BaseModel):
    probability: float = Field(ge=0, le=1)
    positive: bool                     # probability >= порога, выбранного при валидации
    has_evidence: bool = True          # False — ни один ключевой маркер не измерен:
                                       # вероятность априорная, выводу доверять нельзя
    top_features: list[FeatureContribution] = []   # по убыванию |вклада|


class AnalysisResult(BaseModel):
    case_token: str
    model_version: str
    # Уровень 1: жёсткое правило (не ML)
    anemia_detected: bool
    hemoglobin_threshold: float        # порог, с которым сравнивали (г/л)
    # Уровень 2: предсказания модели
    predictions: dict[Condition, ConditionPrediction]
    anemia_class: AnemiaClass
    deficiency_cause: DeficiencyCause
    # 5–7 признаков с наибольшим влиянием на итоговый вывод (для гистограммы)
    key_features: list[KeyFeature] = []
    missing_features: list[str] = []   # неизмеренные показатели, которые использует модель
                                       # (основа для рекомендаций по дообследованию)
