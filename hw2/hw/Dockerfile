
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir prometheus-client prometheus-fastapi-instrumentator

COPY shop_api/ ./shop_api/

EXPOSE 8000


ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]