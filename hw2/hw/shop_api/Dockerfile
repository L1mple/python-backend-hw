FROM python:3.12-slim AS base

ENV APP_ROOT=/app

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip

WORKDIR ${APP_ROOT}/src
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

ENV VIRTUAL_ENV=${APP_ROOT}/src/.venv \
    PATH=${APP_ROOT}/src/.venv/bin:$PATH

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser ${APP_ROOT}/src
USER appuser

FROM base as local

CMD ["uvicorn", "shop_api.main:app", "--port", "8080", "--host", "0.0.0.0"]
