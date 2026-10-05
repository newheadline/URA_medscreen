from typing import Protocol, Sequence

from common.schemas import Condition, ConditionPrediction, DeidentifiedCase


class ModelBackend(Protocol):
    """Всё, что должна реализовать модель, чтобы встать в контур анализа.
    Правиловая заглушка и будущая ML-модель взаимозаменяемы."""

    @property
    def version(self) -> str: ...

    @property
    def used_features(self) -> Sequence[str]:
        """Какие показатели модель реально использует (для missing_features)."""
        ...

    def predict(self, case: DeidentifiedCase) -> dict[Condition, ConditionPrediction]:
        """Предсказание по КАЖДОМУ значению Condition. Анемию не предсказывать:
        она определяется правилом по гемоглобину до вызова модели."""
        ...
