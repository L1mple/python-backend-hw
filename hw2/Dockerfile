FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/hw

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]