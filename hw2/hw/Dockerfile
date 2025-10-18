FROM python:3.10.18-alpine3.22
LABEL service="processing"
EXPOSE 8080
WORKDIR /app
COPY shop_api/requiremets.txt .
RUN pip install --no-cache-dir -r requiremets.txt
COPY shop_api .
CMD ["python", "main.py"]