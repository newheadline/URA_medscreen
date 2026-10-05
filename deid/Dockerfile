FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ ./common/
COPY deid/ ./deid/

# deid.config ищет .env относительно корня проекта:
#   Path(__file__).resolve().parents[1] / ".env"
# → это /app/.env. Файл монтировать/копировать в compose через env_file —
#   он попадёт в окружение контейнера, и pydantic-settings его подхватит.