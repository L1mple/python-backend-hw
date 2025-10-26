# Домашняя работа 4

## Запуск проекта:

```bash
# Запуск БД
cd hw4
docker-compose up db -d

# Установка зависимостей  
pip3 install -r requirements.txt

# Запуск приложения
export DATABASE_URL="postgresql://user:password@localhost:5432/shop_db"
uvicorn shop_api.main:app --reload --port 8000
```

## Тестирование:

### Тест функциональности API:
```bash
./test_api.sh
```

### Тест уровней изоляции транзакций:
```bash
python3 test_isolation_advanced.py
```

