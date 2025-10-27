FROM python:3.12 AS base

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

RUN apt-get update && apt-get install -y gcc
RUN python -m pip install --upgrade pip

WORKDIR /app/src
COPY ./service ./service
COPY ./requirements.txt ./
COPY ./tests ./tests

ENV VIRTUAL_ENV=/app/src/.venv \
    PATH=/app/src/.venv/bin:$PATH
RUN python -m venv $VIRTUAL_ENV

RUN pip install -r requirements.txt

FROM base AS local

CMD ["uvicorn", "service.main:app", "--port", "8080", "--host", "0.0.0.0"]
