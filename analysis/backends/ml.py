"""Adapter from production model artifacts to the existing analysis contract."""

from __future__ import annotations

import math
from pathlib import Path

from analysis.ai import (
    AI,
    MODEL_FEATURES,
    MissingFeaturesError,
    PatientAnalyses,
    TaskConfig,
)
from analysis.backends.rules import RulesBackend
from common.schemas import (
    Condition,
    ConditionPrediction,
    DeidentifiedCase,
    FeatureContribution,
)


MODELS_DIR = Path(__file__).resolve().parents[1] / "models"

MODEL_FILES: dict[Condition, str] = {
    Condition.iron_deficiency: (
        "latent_deficiency_iron_deficiency_test_pr_auc_0.7582.joblib"
    ),
    Condition.b12_deficiency: (
        "B12_deficiency_no_anemia_B12_deficiency_test_pr_auc_0.5746.joblib"
    ),
    Condition.folate_deficiency: (
        "folate_deficiency_no_anemia_folate_deficiency_test_pr_auc_0.2857.joblib"
    ),
    Condition.b6_deficiency: (
        "B6_deficiency_B6_deficiency_test_pr_auc_0.4817.joblib"
    ),
    Condition.copper_deficiency: (
        "copper_deficiency_copper_deficiency_test_pr_auc_0.4444.joblib"
    ),
}

DEFICIENCIES: tuple[Condition, ...] = tuple(MODEL_FILES)


class MLBackend:
    """Five calibrated models plus existing derived/rule-only conditions.

    The five deficiency probabilities and their ``top_features`` come from
    production artifacts.  ``mixed_deficiency`` remains derived from those
    five probabilities, while ``inflammation_anemia`` remains rule-based
    because no production artifact for it was supplied.
    """

    version = "catboost-calibrated-schema3"
    used_features = MODEL_FEATURES

    def __init__(
        self,
        model_dir: str | Path = MODELS_DIR,
        *,
        shap_permutations: int = 10,
        warmup: bool = True,
    ) -> None:
        directory = Path(model_dir).expanduser().resolve()
        self._ai = AI(
            {
                condition.value: TaskConfig(
                    model_path=directory / filename,
                    shap_permutations=shap_permutations,
                )
                for condition, filename in MODEL_FILES.items()
            }
        )
        self._rules = RulesBackend()
        if warmup:
            self._ai.warmup()

    def predict(
        self,
        case: DeidentifiedCase,
    ) -> dict[Condition, ConditionPrediction]:
        patient = self._patient(case)
        predictions: dict[Condition, ConditionPrediction] = {}
        for condition in DEFICIENCIES:
            result = self._ai.predict(condition.value, patient)
            contributions = [
                FeatureContribution(
                    feature=item["feature"],
                    value=item["value"],
                    contribution=item["contribution"],
                )
                for item in result["shap"]["contributions"]
            ]
            predictions[condition] = ConditionPrediction(
                probability=result["calibrated_probability"],
                positive=result["positive"],
                has_evidence=True,
                top_features=contributions,
            )

        # There is no supplied production model for inflammation.  Preserve
        # the contract with the existing clinical rule until one is provided.
        predictions[Condition.inflammation_anemia] = self._rules.predict(case)[
            Condition.inflammation_anemia
        ]
        predictions[Condition.mixed_deficiency] = self._mixed(predictions)
        return predictions

    @staticmethod
    def _patient(case: DeidentifiedCase) -> PatientAnalyses:
        values: dict[str, float | str | None] = {
            "age_years": case.age_years,
            "sex": case.sex.value,
            **{
                feature: getattr(case.labs, feature)
                for feature in MODEL_FEATURES
                if feature not in {"age_years", "sex"}
            },
        }
        missing = [feature for feature in MODEL_FEATURES if values[feature] is None]
        if missing:
            raise MissingFeaturesError(missing)
        return PatientAnalyses(**values)  # type: ignore[arg-type]

    @staticmethod
    def _mixed(
        predictions: dict[Condition, ConditionPrediction],
    ) -> ConditionPrediction:
        probabilities = [predictions[condition].probability for condition in DEFICIENCIES]
        probability_none = math.prod(1 - value for value in probabilities)
        probability_one = sum(
            value
            * math.prod(
                1 - other
                for other_index, other in enumerate(probabilities)
                if other_index != index
            )
            for index, value in enumerate(probabilities)
        )
        positive_count = sum(
            predictions[condition].positive for condition in DEFICIENCIES
        )
        return ConditionPrediction(
            probability=max(0.0, min(1.0, 1 - probability_none - probability_one)),
            positive=positive_count >= 2,
            has_evidence=True,
            top_features=[],
        )


__all__ = ["MLBackend", "MODELS_DIR", "MODEL_FILES"]
