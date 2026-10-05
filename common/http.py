from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def sanitized_validation_handler(_: Request, exc: Exception):
    """По умолчанию FastAPI возвращает во входе ("input") сами значения —
    это утечка данных в ответ и логи прокси. Отдаём только поле и причину."""
    assert isinstance(exc, RequestValidationError)
    errors = [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})
