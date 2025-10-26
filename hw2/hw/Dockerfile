
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir prometheus-client prometheus-fastapi-instrumentator

COPY shop_api/ ./shop_api/
COPY transaction_isolation_demo.py .
COPY test_homework2_all.py .
COPY setup.py .

# Устанавливаем пакет shop_api
RUN pip install -e .

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]