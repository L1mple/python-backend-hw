# ДЗ 4

1. Запуск приложения и БД
```sh
# Postgres
docker compose up

# Окружение
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Миграции и запуск приложения
source scripts/start.sh
```

2. Запуск скриптов для демонстрации проблем с транзакциями:
```sh
export PYTHONPATH=${PWD}/src/
python transactions_problems_scripts/transactions_problems_scripts.py
```