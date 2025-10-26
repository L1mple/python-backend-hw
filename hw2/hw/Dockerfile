FROM python:3.12 AS base

RUN python -m pip install --upgrade pip

WORKDIR /app
COPY .  ./

RUN pip install -r requirements.txt

FROM base as local

CMD ["uvicorn", "shop_api.main:app", "--port", "8080", "--host", "0.0.0.0"]
