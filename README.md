



## Lecture 4: База данных и транзакции
- Переписан `hw2/hw/shop_api/main.py` с SQLAlchemy + SQLite
- Обновлён `hw2/docker-compose.yml` с volume для SQLite
- Создан `lecture4/transaction_demo.py` с демонстрацией уровней изоляции транзакций

### Как запустить

1. **Демонстрация транзакций:**
```bash
python lecture4/transaction_demo.py
```

2. **Запуск API с БД:**
```bash
cd hw2
docker compose up -d --build
```
### Что показывает демо транзакций

- **Dirty Read** при READ UNCOMMITTED
- **Отсутствие Dirty Read** при READ COMMITTED
- **Non-repeatable Read** при READ COMMITTED
- **Отсутствие Non-repeatable Read** при REPEATABLE READ
- **Phantom Reads** при REPEATABLE READ
- **Отсутствие Phantom Reads** при SERIALIZABLE

## Lecture 5: Тесты и CI

### Что реализовано

- Создан `lecture5/hw/test_lecture5.py` с 11 тестами для покрытия кода
- Создан `.github/workflows/lecture5-tests.yml` для CI
- Тесты покрывают все эндпоинты, валидацию, ошибки, WebSocket, модели БД

### Как запустить тесты

1. **Локальный запуск:**
```bash
# Установите зависимости
pip install pytest-cov sqlalchemy

# Запустите тесты
pytest lecture5/hw/test_lecture5.py -v

# С покрытием кода
pytest --cov=shop_api.main --cov-report=term lecture5/hw/test_lecture5.py
```

2. **Проверка существующих тестов hw2:**
```bash
# Установите PYTHONPATH
$env:PYTHONPATH = "C:\Users\zhiga\python-backend-hw\hw2\hw"

# Запустите тесты
pytest hw2/hw/test_homework2.py -v
```


