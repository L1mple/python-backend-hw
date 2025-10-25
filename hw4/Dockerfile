FROM python:3.12 AS base
# базовый образ python 3.12

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500
# настройки python и pip

RUN apt-get update && apt-get install -y gcc
# установка gcc для python-пакетов

RUN python -m pip install --upgrade pip
# обновление pip

WORKDIR /app/src
# рабочая директория

COPY ./shop_api ./shop_api
COPY ./requirements.txt .
# копирование только нужных файлов

ENV VIRTUAL_ENV=/app/src/.venv \
    PATH=/app/src/.venv/bin:$PATH
# виртуальное окружение

RUN pip install -r requirements.txt
# установка зависимостей

FROM base as local
# stage для запуска

CMD ["uvicorn", "shop_api.main:app", "--port", "8000", "--host", "0.0.0.0"]
# запуск uvicorn