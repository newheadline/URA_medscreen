import hmac
import logging

from functools import lru_cache

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.exceptions import RequestValidationError

from analysis.backends.rules import RulesBackend
from analysis.config import AnalysisSettings
from analysis.service import Analyzer
from common.http import sanitized_validation_handler
from common.schemas import AnalysisResult, DeidentifiedCase

from analysis.backends.ml import MLBackend
from analysis.backends.rules import RulesBackend

# Этот модуль НЕ импортирует deid.* и common.labs-хранилища: ни идентификаторов,
# ни ключей шифрования здесь нет (проверяется тестом test_analysis_isolation).
logger = logging.getLogger("analysis")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Analysis contour", docs_url=None, redoc_url=None)
app.add_exception_handler(RequestValidationError, sanitized_validation_handler)


@lru_cache
def _settings() -> AnalysisSettings:
    return AnalysisSettings()  # pyright: ignore[reportCallIssue]



@lru_cache
def _analyzer() -> Analyzer:
    backend = _settings().model_backend
    if backend == "rules":
        return Analyzer(RulesBackend())
    if backend == "ml":
        return Analyzer(MLBackend())
    raise RuntimeError(f"unknown MODEL_BACKEND={backend!r}")

@app.on_event("startup")
def _warmup() -> None:
    """Загрузка моделей до первого запроса. Если артефакты битые — падаем
    сразу, а не при попытке обработать пациента."""
    _analyzer()

def require_api_key(
    x_api_key: str = Header(...),
    s: AnalysisSettings = Depends(_settings),
) -> None:
    if not hmac.compare_digest(x_api_key, s.analysis_api_key.get_secret_value()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid api key")


@app.post("/v1/analyze", response_model=AnalysisResult,
          dependencies=[Depends(require_api_key)])
def analyze(case: DeidentifiedCase,
            analyzer: Analyzer = Depends(_analyzer)) -> AnalysisResult:
    result = analyzer.analyze(case)        # sync-эндпоинт: FastAPI уводит в threadpool
    logger.info("analyzed case=%s model=%s", case.case_token, result.model_version)
    return result


@app.get("/health")
def health(analyzer: Analyzer = Depends(_analyzer)) -> dict[str, str]:
    return {"status": "ok", "model_version": analyzer.backend.version}


