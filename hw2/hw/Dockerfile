FROM python:3.12 AS base

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /shop_api

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . ./

ENV VIRTUAL_ENV=$APP_ROOT/src/.venv \
    PATH=$APP_ROOT/src/.venv/bin:$PATH

FROM base as local

# Запуск приложения
# hot-reload
CMD ["uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
