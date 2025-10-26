FROM python:3.12

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

RUN apt-get update && apt-get install -y gcc
RUN python -m pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY ./hw2 /app/hw2

EXPOSE 8000

CMD ["uvicorn", "hw2.rest_example.main:app", "--host", "0.0.0.0", "--port", "8000"]