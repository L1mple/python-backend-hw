FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

ENV VIRTUAL_ENV=$APP_ROOT/.venv \
    PATH=$APP_ROOT/.venv/bin:$PATH

RUN pip install --no-cache-dir -r requirements.txt

COPY shop_api/ ./src/

EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]