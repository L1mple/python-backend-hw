FROM python:3.13.7 AS base

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

ENV APP_ROOT=/app

RUN apt-get update && apt-get install -y gcc
RUN python -m pip install --upgrade pip

WORKDIR $APP_ROOT/src

ENV VIRTUAL_ENV=$APP_ROOT/src/.venv \
    PATH=$APP_ROOT/src/.venv/bin:$PATH

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

FROM base AS local

CMD ["uvicorn", "shop_api.main:app", "--port", "8080", "--host", "0.0.0.0"]
