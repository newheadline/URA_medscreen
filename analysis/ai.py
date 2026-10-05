"""Production inference for the screening CatBoost artifacts.

The public HTTP contract lives in ``common.schemas``.  This module is kept
independent from FastAPI and converts one strict, fixed-width patient row into
calibrated probabilities plus local permutation-SHAP contributions expressed
in probability units.

``joblib`` uses pickle internally.  Only trusted artifacts shipped with the
service may be loaded here.
"""

from __future__ import annotations

import platform
import threading
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

import catboost
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.exceptions import InconsistentVersionWarning


# The order is part of the serialized-model contract.
MODEL_FEATURES: tuple[str, ...] = (
    "age_years",
    "sex",
    "hemoglobin",
    "RBC",
    "hematocrit",
    "MCV",
    "MCH",
    "MCHC",
    "platelets",
    "WBC",
    "RDW",
)
NUMERIC_FEATURES: tuple[str, ...] = tuple(
    feature for feature in MODEL_FEATURES if feature != "sex"
)
CATEGORICAL_FEATURES: tuple[str, ...] = ("sex",)
ARTIFACT_SCHEMA_VERSION = 3


class AIError(RuntimeError):
    """Base inference error."""


class UnknownTaskError(AIError):
    """No model is registered for the requested task."""


class ModelArtifactError(AIError):
    """A model artifact is missing, incompatible, or malformed."""


class PatientDataError(AIError):
    """The patient row cannot be passed to the model."""


class MissingFeaturesError(PatientDataError):
    """One or more of the fixed model features have no value."""

    def __init__(self, features: list[str]) -> None:
        self.features = features
        super().__init__(
            "missing required model features: " + ", ".join(features)
        )


@dataclass(frozen=True)
class PatientAnalyses:
    """Exactly the eleven values required by every production model."""

    age_years: float
    sex: str
    hemoglobin: float
    RBC: float
    hematocrit: float
    MCV: float
    MCH: float
    MCHC: float
    platelets: float
    WBC: float
    RDW: float


@dataclass(frozen=True)
class TaskConfig:
    """Files and inference settings for one binary classification task."""

    model_path: str | Path
    decision_threshold: float | None = None
    shap_permutations: int = 10
    random_state: int = 42

    def __post_init__(self) -> None:
        if self.decision_threshold is not None and not (
            0 < self.decision_threshold < 1
        ):
            raise ValueError("decision_threshold must be inside (0, 1)")
        if self.shap_permutations < 1:
            raise ValueError("shap_permutations must be at least 1")


@dataclass(frozen=True)
class _LoadedTask:
    config: TaskConfig
    artifact: Mapping[str, Any]
    calibrated_model: Any
    shap_background: pd.DataFrame
    decision_threshold: float


class AI:
    """Registry of binary screening models with calibrated SHAP inference."""

    def __init__(self, tasks: Mapping[str, TaskConfig]) -> None:
        if not tasks:
            raise ValueError("tasks must not be empty")
        self._tasks: dict[str, TaskConfig] = {}
        self._loaded: dict[str, _LoadedTask] = {}
        self._load_lock = threading.RLock()
        for task, config in tasks.items():
            if not isinstance(task, str) or not task.strip():
                raise TypeError("task names must be non-empty strings")
            if not isinstance(config, TaskConfig):
                raise TypeError("every task must contain TaskConfig")
            self._tasks[task.strip()] = config

    @property
    def available_tasks(self) -> tuple[str, ...]:
        return tuple(sorted(self._tasks))

    def warmup(self) -> None:
        """Load and validate every configured artifact before serving traffic."""
        for task in self.available_tasks:
            self._load_task(task)

    def predict(self, task: str, patient: PatientAnalyses) -> dict[str, Any]:
        if not isinstance(task, str) or not task.strip():
            raise UnknownTaskError("task must be a non-empty string")
        task = task.strip()
        loaded = self._load_task(task)
        raw_patient = self._patient_frame(patient)
        patient_frame = self._prepare_for_model(raw_patient, loaded.artifact)
        probability = float(
            self._positive_probability(loaded.calibrated_model, patient_frame)[0]
        )
        base_probability, contributions = self._probability_shap(
            loaded,
            patient_frame,
            probability,
        )

        absolute_total = float(np.abs(contributions).sum())
        order = np.argsort(np.abs(contributions))[::-1]
        shap_values: list[dict[str, Any]] = []
        for index in order:
            feature = MODEL_FEATURES[int(index)]
            contribution = float(contributions[index])
            shap_values.append(
                {
                    "feature": feature,
                    "value": self._json_value(patient_frame.iloc[0][feature]),
                    "contribution": contribution,
                    "absolute_contribution": abs(contribution),
                    "importance": (
                        abs(contribution) / absolute_total
                        if absolute_total > 0
                        else 0.0
                    ),
                    "direction": (
                        "increases_probability"
                        if contribution > 0
                        else "decreases_probability"
                        if contribution < 0
                        else "neutral"
                    ),
                }
            )

        explained_probability = float(base_probability + contributions.sum())
        return {
            "task": task,
            "calibrated_probability": probability,
            "decision_threshold": loaded.decision_threshold,
            "positive": probability >= loaded.decision_threshold,
            "shap": {
                "method": "permutation_shap_calibrated_probability",
                "base_probability": base_probability,
                "contributions": shap_values,
                "explained_probability": explained_probability,
                "additivity_error": probability - explained_probability,
            },
        }

    @staticmethod
    def _existing_file(path: str | Path) -> Path:
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise ModelArtifactError(f"model artifact not found: {resolved}")
        return resolved

    @staticmethod
    def _load_artifact(model_path: str | Path) -> Mapping[str, Any]:
        path = AI._existing_file(model_path)
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "error",
                    category=InconsistentVersionWarning,
                )
                artifact = joblib.load(path)
        except InconsistentVersionWarning as exc:
            raise ModelArtifactError(
                "model artifact was created with scikit-learn "
                f"{exc.original_sklearn_version}, runtime uses "
                f"{exc.current_sklearn_version}"
            ) from exc
        except Exception as exc:
            raise ModelArtifactError(
                f"failed to load model artifact {path}: {exc}"
            ) from exc
        if not isinstance(artifact, Mapping):
            raise ModelArtifactError("model artifact must be a mapping")
        if artifact.get("artifact_schema_version") != ARTIFACT_SCHEMA_VERSION:
            raise ModelArtifactError(
                "unsupported model artifact schema: "
                f"{artifact.get('artifact_schema_version')!r}; "
                f"expected {ARTIFACT_SCHEMA_VERSION}"
            )

        required = {
            "runtime_versions",
            "calibrated_model",
            "features",
            "numerical_features",
            "categorical_features",
            "numeric_imputer",
            "categorical_imputer",
            "results",
            "shap_background",
        }
        missing = sorted(required - set(artifact))
        if missing:
            raise ModelArtifactError(
                "model artifact is missing keys: " + ", ".join(missing)
            )

        AI._validate_runtime_versions(artifact["runtime_versions"])
        features = tuple(str(value) for value in artifact["features"])
        numerical = tuple(str(value) for value in artifact["numerical_features"])
        categorical = tuple(
            str(value) for value in artifact["categorical_features"]
        )
        if features != MODEL_FEATURES:
            raise ModelArtifactError(
                f"model features are {features!r}, expected {MODEL_FEATURES!r}"
            )
        if numerical != NUMERIC_FEATURES or categorical != CATEGORICAL_FEATURES:
            raise ModelArtifactError(
                "model numerical/categorical feature groups do not match"
            )

        calibrated_model = artifact["calibrated_model"]
        if not callable(getattr(calibrated_model, "predict_proba", None)):
            raise ModelArtifactError(
                "calibrated_model must provide predict_proba"
            )
        for key in ("numeric_imputer", "categorical_imputer"):
            if not callable(getattr(artifact[key], "transform", None)):
                raise ModelArtifactError(f"{key} must provide transform")

        background = artifact["shap_background"]
        if not isinstance(background, pd.DataFrame) or background.empty:
            raise ModelArtifactError("shap_background must be a non-empty DataFrame")
        if tuple(background.columns) != MODEL_FEATURES:
            raise ModelArtifactError(
                "shap_background columns do not match model features"
            )
        return artifact

    @staticmethod
    def _validate_runtime_versions(runtime_versions: Any) -> None:
        if not isinstance(runtime_versions, Mapping):
            raise ModelArtifactError("runtime_versions must be a mapping")
        current = {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "catboost": catboost.__version__,
            "joblib": joblib.__version__,
        }
        def compatible(name: str, artifact: Any, runtime: str) -> bool:
            if name != "python":
                return artifact == runtime
            # Pickle format is stable across CPython 3.x for pure-Python
            # objects (sklearn/catboost wrappers).  The artifact already
            # loaded successfully, so we only require the same major line.
            try:
                artifact_major = str(artifact).split(".")[0]
                runtime_major = runtime.split(".")[0]
            except (ValueError, AttributeError):
                return False
            return artifact_major == runtime_major
        mismatches = [
            f"{name}: artifact={runtime_versions.get(name)!r}, runtime={version!r}"
            for name, version in current.items()
            if not compatible(name, runtime_versions.get(name), version)
        ]
        if mismatches:
            raise ModelArtifactError(
                "model artifact runtime mismatch: " + "; ".join(mismatches)
            )

    @staticmethod
    def _decision_threshold(artifact: Mapping[str, Any]) -> float:
        results = artifact.get("results")
        thresholds = results.get("thresholds") if isinstance(results, Mapping) else None
        if not isinstance(thresholds, pd.DataFrame) or thresholds.empty:
            raise ModelArtifactError("results.thresholds must be a non-empty DataFrame")
        required = {"threshold", "balanced_accuracy", "f1"}
        missing = sorted(required - set(thresholds.columns))
        if missing:
            raise ModelArtifactError(
                "results.thresholds is missing columns: " + ", ".join(missing)
            )
        best = thresholds.sort_values(
            ["balanced_accuracy", "f1", "threshold"],
            ascending=[False, False, True],
        ).iloc[0]
        threshold = float(best["threshold"])
        if not 0 < threshold < 1:
            raise ModelArtifactError("selected decision threshold is outside (0, 1)")
        return threshold

    def _load_task(self, task: str) -> _LoadedTask:
        if task not in self._tasks:
            available = ", ".join(self.available_tasks)
            raise UnknownTaskError(
                f"no model for task {task!r}; available: {available}"
            )
        loaded = self._loaded.get(task)
        if loaded is not None:
            return loaded

        with self._load_lock:
            loaded = self._loaded.get(task)
            if loaded is not None:
                return loaded
            config = self._tasks[task]
            artifact = self._load_artifact(config.model_path)
            background = self._prepare_for_model(
                artifact["shap_background"],
                artifact,
            )
            threshold = (
                config.decision_threshold
                if config.decision_threshold is not None
                else self._decision_threshold(artifact)
            )
            loaded = _LoadedTask(
                config=config,
                artifact=artifact,
                calibrated_model=artifact["calibrated_model"],
                shap_background=background,
                decision_threshold=threshold,
            )
            self._loaded[task] = loaded
            return loaded

    @staticmethod
    def _patient_frame(patient: PatientAnalyses) -> pd.DataFrame:
        if not isinstance(patient, PatientAnalyses):
            raise TypeError("patient must be PatientAnalyses")
        values = asdict(patient)
        missing = [
            feature
            for feature in MODEL_FEATURES
            if values[feature] is None
            or (
                not isinstance(values[feature], str)
                and bool(pd.isna(values[feature]))
            )
        ]
        if missing:
            raise MissingFeaturesError(missing)
        return pd.DataFrame([values], columns=MODEL_FEATURES)

    @staticmethod
    def _normalise_raw_frame(frame: pd.DataFrame) -> pd.DataFrame:
        prepared = frame.loc[:, MODEL_FEATURES].copy()
        invalid_numeric: dict[str, list[str]] = {}
        for feature in NUMERIC_FEATURES:
            source = prepared[feature]
            numeric = pd.to_numeric(source, errors="coerce")
            invalid = source.notna() & (numeric.isna() | ~np.isfinite(numeric))
            if invalid.any():
                invalid_numeric[feature] = (
                    source.loc[invalid]
                    .astype(str)
                    .drop_duplicates()
                    .head(5)
                    .tolist()
                )
            prepared[feature] = numeric
        if invalid_numeric:
            details = "; ".join(
                f"{feature}: {values!r}"
                for feature, values in invalid_numeric.items()
            )
            raise PatientDataError("invalid numeric values: " + details)

        prepared["sex"] = prepared["sex"].map(
            lambda value: str(value).strip().upper()
        )
        invalid_sex = ~prepared["sex"].isin(("M", "F"))
        if invalid_sex.any():
            values = prepared.loc[invalid_sex, "sex"].unique().tolist()
            raise PatientDataError(f"sex must be 'M' or 'F'; got {values!r}")
        return prepared

    @staticmethod
    def _prepare_for_model(
        raw_frame: pd.DataFrame,
        artifact: Mapping[str, Any],
    ) -> pd.DataFrame:
        frame = AI._normalise_raw_frame(raw_frame)
        try:
            numeric = np.asarray(
                artifact["numeric_imputer"].transform(
                    frame.loc[:, NUMERIC_FEATURES]
                ),
                dtype=float,
            )
            categorical = np.asarray(
                artifact["categorical_imputer"].transform(
                    frame.loc[:, CATEGORICAL_FEATURES]
                ),
                dtype=object,
            )
        except Exception as exc:
            raise PatientDataError(f"model preprocessing failed: {exc}") from exc

        if numeric.shape != (len(frame), len(NUMERIC_FEATURES)):
            raise ModelArtifactError("numeric_imputer returned an invalid shape")
        if categorical.shape != (len(frame), len(CATEGORICAL_FEATURES)):
            raise ModelArtifactError("categorical_imputer returned an invalid shape")
        if not np.isfinite(numeric).all():
            raise PatientDataError("model preprocessing produced NaN/inf")

        result = frame.copy()
        for index, feature in enumerate(NUMERIC_FEATURES):
            result[feature] = numeric[:, index]
        result["sex"] = [str(value) for value in categorical[:, 0]]
        if (~result["sex"].isin(("M", "F"))).any():
            raise PatientDataError("model preprocessing produced an invalid sex value")
        return result.loc[:, MODEL_FEATURES]

    @staticmethod
    def _positive_probability(model: Any, frame: pd.DataFrame) -> np.ndarray:
        try:
            probabilities = np.asarray(model.predict_proba(frame), dtype=float)
        except Exception as exc:
            raise PatientDataError(f"predict_proba failed: {exc}") from exc
        if probabilities.ndim != 2:
            raise ModelArtifactError("predict_proba must return a 2D array")
        classes = list(getattr(model, "classes_", []))
        if 1 not in classes:
            raise ModelArtifactError(
                f"calibrated model has no positive class 1: {classes!r}"
            )
        result = probabilities[:, classes.index(1)]
        if not np.isfinite(result).all():
            raise PatientDataError("model returned NaN/inf probability")
        if np.any((result < 0) | (result > 1)):
            raise ModelArtifactError("predict_proba returned a value outside [0, 1]")
        return result

    def _probability_shap(
        self,
        loaded: _LoadedTask,
        patient_frame: pd.DataFrame,
        probability: float,
    ) -> tuple[float, np.ndarray]:
        background = loaded.shap_background
        base_probability = float(
            self._positive_probability(
                loaded.calibrated_model,
                background,
            ).mean()
        )
        contributions = np.zeros(len(MODEL_FEATURES), dtype=float)
        rng = np.random.default_rng(loaded.config.random_state)

        permutations: list[np.ndarray] = []
        while len(permutations) < loaded.config.shap_permutations:
            order = rng.permutation(len(MODEL_FEATURES))
            permutations.append(order)
            if len(permutations) < loaded.config.shap_permutations:
                permutations.append(order[::-1])

        for order in permutations:
            current = background.copy()
            previous = base_probability
            for feature_index in order:
                feature = MODEL_FEATURES[int(feature_index)]
                current[feature] = patient_frame.iloc[0][feature]
                current_probability = float(
                    self._positive_probability(
                        loaded.calibrated_model,
                        current,
                    ).mean()
                )
                contributions[feature_index] += current_probability - previous
                previous = current_probability

        contributions /= len(permutations)
        correction = probability - (base_probability + contributions.sum())
        correction_index = int(np.argmax(np.abs(contributions)))
        contributions[correction_index] += correction
        return base_probability, contributions

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, np.generic):
            value = value.item()
        if pd.isna(value):
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        return str(value)


__all__ = [
    "AI",
    "AIError",
    "ARTIFACT_SCHEMA_VERSION",
    "CATEGORICAL_FEATURES",
    "MODEL_FEATURES",
    "MissingFeaturesError",
    "ModelArtifactError",
    "NUMERIC_FEATURES",
    "PatientAnalyses",
    "PatientDataError",
    "TaskConfig",
    "UnknownTaskError",
]
