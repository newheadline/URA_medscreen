class AccessDenied(Exception):
    """Нет права на объект/действие → HTTP 403 + запись DENIED в журнал аудита."""


class NotFound(Exception):
    """Объект не существует в пределах доступного пользователю → HTTP 404."""


class DuplicateOms(Exception):
    """Пациент с таким ОМС уже зарегистрирован."""


class Unprocessable(Exception):
    """Нарушено бизнес-правило → HTTP 422; code — машинное имя для фронтенда."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
