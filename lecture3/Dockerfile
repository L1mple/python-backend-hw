FROM python:3.12 AS base

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --upgrade pip

COPY ./shop_api/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY ./shop_api ./shop_api

FROM base AS local

CMD ["uvicorn", "shop_api.main:app", "--port", "8080", "--host", "0.0.0.0"]
