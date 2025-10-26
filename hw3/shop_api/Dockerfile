FROM python:3.12-slim AS base

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y gcc

# Обновляем pip
RUN python -m pip install --upgrade pip

# Создаем и настраиваем рабочую директорию
ENV APP_ROOT=/app
WORKDIR $APP_ROOT

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем исходный код
COPY src/ .

FROM base as local
