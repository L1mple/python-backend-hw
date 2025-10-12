FROM python:3.13
LABEL authors="Aleksandra Tsepkova"

WORKDIR /hw

COPY requirements.txt .
RUN pip install -r requirements.txt


COPY . ./

EXPOSE 8080
ENTRYPOINT ["uvicorn", "shop_api.main:app", "--host", "0.0.0.0", "--port", "8080"]