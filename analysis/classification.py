"""Итоговый вывод: (anemia_class, deficiency_cause) по флагам модели.

СЕМАНТИКА ЧАСТИ МЕТОК — ПРЕДПОЛОЖЕНИЕ (в первых 100 строках датасета есть
только B12-метки). Проверить на полном датасете: таблица
флаги → (anemia_class, deficiency_cause) должна восстанавливаться однозначно.
Спорные места помечены ASSUMPTION."""
from dataclasses import dataclass

from common.schemas import (AnemiaClass, Condition, ConditionPrediction,
                            DeficiencyCause)

IRON, B12, FOLATE = (Condition.iron_deficiency, Condition.b12_deficiency,
                     Condition.folate_deficiency)
B6, COPPER = Condition.b6_deficiency, Condition.copper_deficiency

DEFICIENCIES = (IRON, B12, FOLATE, B6, COPPER)

SINGLE_CAUSE = {
    IRON: DeficiencyCause.iron, B12: DeficiencyCause.b12,
    FOLATE: DeficiencyCause.folate, B6: DeficiencyCause.b6,
    COPPER: DeficiencyCause.copper,
}
# В списке причин есть ТОЛЬКО три пары. Сочетания с B6/медью и тройные
# в словаре значений отсутствуют → fallback "undetermined" (ASSUMPTION).
PAIR_CAUSE = {
    frozenset({IRON, B12}): DeficiencyCause.iron_b12,
    frozenset({IRON, FOLATE}): DeficiencyCause.iron_folate,
    frozenset({B12, FOLATE}): DeficiencyCause.b12_folate,
}
CLASS_WITH_ANEMIA = {
    IRON: AnemiaClass.iron_anemia, B12: AnemiaClass.b12_anemia,
    FOLATE: AnemiaClass.folate_anemia,
    B6: AnemiaClass.b6, COPPER: AnemiaClass.copper,     # суффикса «_anemia» нет
}
CLASS_NO_ANEMIA = {
    B12: AnemiaClass.b12_no_anemia, FOLATE: AnemiaClass.folate_no_anemia,
    IRON: AnemiaClass.latent,           # ASSUMPTION: латентный дефицит железа
    B6: AnemiaClass.b6, COPPER: AnemiaClass.copper,
}


@dataclass(frozen=True)
class Verdict:
    anemia_class: AnemiaClass
    cause: DeficiencyCause
    implicated: tuple[Condition, ...]   # какие условия объясняют вывод


def classify(anemic: bool, preds: dict[Condition, ConditionPrediction]) -> Verdict:
    defs = tuple(c for c in DEFICIENCIES if preds[c].positive)
    mixed = len(defs) >= 2 or preds[Condition.mixed_deficiency].positive
    inflammation = anemic and preds[Condition.inflammation_anemia].positive

    # ── причина ──
    if len(defs) == 1 and not mixed:
        cause = SINGLE_CAUSE[defs[0]]
    elif mixed:
        cause = PAIR_CAUSE.get(frozenset(defs), DeficiencyCause.undetermined)
    elif inflammation:
        cause = DeficiencyCause.inflammation
    elif anemic:
        cause = DeficiencyCause.undetermined
    else:
        cause = DeficiencyCause.none

    # ── класс ──
    if mixed:
        cls = AnemiaClass.mixed            # ASSUMPTION: и при отсутствии анемии
    elif len(defs) == 1:
        table = CLASS_WITH_ANEMIA if anemic else CLASS_NO_ANEMIA
        cls = table[defs[0]]
    elif inflammation:
        cls = AnemiaClass.inflammation_anemia
    elif anemic:
        cls = AnemiaClass.anemia_other
    else:
        cls = AnemiaClass.no_anemia_no_deficiency

    if defs:
        implicated: tuple[Condition, ...] = defs
    elif cause == DeficiencyCause.inflammation:
        implicated = (Condition.inflammation_anemia,)
    elif mixed:
        implicated = (Condition.mixed_deficiency,)
    else:
        implicated = ()
    return Verdict(cls, cause, implicated)
