FROM python:3.12-slim

WORKDIR /api

RUN apt-get update -y

COPY requirements_hw3.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
