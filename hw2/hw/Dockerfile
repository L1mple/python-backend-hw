FROM python:3.12 AS base

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --upgrade pip

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

ENV PYTHONPATH=/app

FROM base as local

EXPOSE 8080

CMD ["uvicorn", "shop_api.main:app", "--port", "8080", "--host", "0.0.0.0"]

