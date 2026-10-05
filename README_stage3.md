# Запуск (из папки medscreen/)

    # 1. БД хранилища
    docker compose -f docker-compose.vault.yml up -d
    # 2. analysis/.env  (ANALYSIS_API_KEY — то же значение, что в .env обезличивания)
    cp analysis/.env.example analysis/.env
    # 3. сервисы (два терминала)
    uvicorn analysis.main:app --port 8002
    uvicorn deid.main:app --port 8001
    # 4. проверка
    python -m pytest -q
