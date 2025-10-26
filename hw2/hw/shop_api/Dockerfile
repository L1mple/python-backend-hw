FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app/shop_api

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
