FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shop_api/ ./shop_api/

CMD ["uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]