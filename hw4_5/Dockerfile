FROM python:3.12


RUN apt-get update && apt-get install -y gcc
RUN python -m pip install --upgrade pip

WORKDIR app
COPY . .

RUN pip install -r requirements.txt

RUN chmod -R +x scripts/start.sh .

ENTRYPOINT [ "sh", "scripts/start.sh" ]