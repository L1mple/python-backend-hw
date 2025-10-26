FROM python:3.12

ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

RUN apt-get update && apt-get install -y gcc
RUN python -m pip install --upgrade pip

WORKDIR /app/src
COPY . ./

RUN pip install -r requirements.txt

CMD ["uvicorn", "shop_api.main:app", "--port", "8088", "--host", "0.0.0.0"]
