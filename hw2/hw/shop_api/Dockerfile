FROM python:3.11-slim
WORKDIR /app
COPY . ./shop_api
RUN pip install --no-cache-dir -r ./shop_api/requirements.txt
EXPOSE 8000
CMD ["uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
