FROM python:3.12 AS base

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

RUN apt-get update && apt-get install -y gcc
RUN python -m pip install --upgrade pip

WORKDIR /app
COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY shop_api/ ./shop_api/

FROM base as local

WORKDIR /app/shop_api
CMD ["uvicorn", "main:app", "--port", "8000", "--host", "0.0.0.0"]