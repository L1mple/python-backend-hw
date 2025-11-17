FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UVICORN_WORKERS=1

WORKDIR /app

# Install build deps for grpcio if needed
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000 50051

# Run FastAPI (serves /metrics) and starts gRPC on startup event
CMD ["python", "-m", "uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]


