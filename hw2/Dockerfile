FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

COPY hw2/hw/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install prometheus-fastapi-instrumentator "uvicorn[standard]"

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "hw2.hw.shop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]


