FROM python:3.12-alpine

## Dependencies installation
RUN python -m pip install --upgrade pip

## Working directory setup
WORKDIR /App

## Copy all the files into the container
COPY . ./

RUN pip install -r requirements.txt

CMD ["uvicorn", "shop_api.main:app", "--port", "8080", "--host", "0.0.0.0"]

