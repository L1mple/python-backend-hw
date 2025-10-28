FROM python:3.12-slim

# Устанавливаем Postgres-клиент (для pg_isready)
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-traditional postgresql-client && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё приложение
COPY . .

# Делаем скрипт ожидания исполняемым
RUN chmod +x wait-for-postgres.sh

# Запускаем сервер через скрипт ожидания
CMD ["./wait-for-postgres.sh", "db", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
