"""Уровень 1: анемия — ЖЁСТКОЕ ПРАВИЛО, не ML.
Пороги — из постановки кейса (критерии ВОЗ): Hb < 120 г/л у женщин и
< 130 г/л у мужчин. На данных проверено: метка `anemia` в датасете
воспроизводится этим правилом на 100 %."""
from common.schemas import Sex

HB_LOW_MALE = 130.0      # г/л
HB_LOW_FEMALE = 120.0    # г/л
# ДОПОЛНЕНИЕ к постановке кейса (критерий ВОЗ для беременных); применяется
# только если во входе явно указано pregnant=true.
HB_LOW_PREGNANT = 110.0  # г/л


def hb_threshold(sex: Sex, pregnant: bool | None) -> float:
    if pregnant:
        return HB_LOW_PREGNANT
    return HB_LOW_FEMALE if sex == Sex.female else HB_LOW_MALE


def is_anemic(hemoglobin: float, sex: Sex, pregnant: bool | None) -> bool:
    return hemoglobin < hb_threshold(sex, pregnant)
