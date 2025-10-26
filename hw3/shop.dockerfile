# FROM python:3.13

# WORKDIR /shop-api
# COPY db.py ./
# COPY main.py ./
# COPY requirements.txt ./

# RUN pip install -r requirements.txt
# RUN uvicorn main:app --reload

FROM python:3.13

WORKDIR /shop-api

# Copies all files from your project directory into the container
COPY . .  

RUN pip install -r requirements.txt

# CMD задаёт команду по умолчанию при запуске контейнера.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
