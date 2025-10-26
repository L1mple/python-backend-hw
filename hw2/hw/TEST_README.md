# Тесты для Домашки 2

## Структура тестов

```
test-hw/
├── __init__.py
├── test_cart_routes.py      # Тесты для cart endpoints
├── test_contracts.py         # Тесты для Pydantic моделей
├── test_database.py          # Тесты для БД моделей
├── test_db_storage.py        # Тесты для DBStorage (мокирование БД)
├── test_item_routes.py       # Тесты для item endpoints
├── test_main.py              # Тесты для FastAPI app
└── test_storage.py           # Тесты для dataclasses
```

## Установка зависимостей

```bash
# Используя uv (рекомендуется)
uv pip install -r requirements.txt

# Или через pip
pip install -r requirements.txt
```

## Запуск тестов локально

### Все тесты с отчетом о покрытии

```bash
PYTHONPATH=/Users/bogdanminko/Study/python-backend/python-backend-hw/hw2/hw \
uv run pytest test-hw/ --cov=shop_api --cov-report=term-missing --cov-report=html -v
```

### Только запуск тестов

```bash
uv run pytest test-hw/ -v

# или

```bash
uv run pytest test-hw/ --cov=shop_api
```

## Continuous Integration (CI)

GitHub Actions автоматически запускает тесты при:
- Push в ветки `main` и `hw-4`
- Создании Pull Request в `main`

Конфигурация CI находится в `.github/workflows/tests.yml`

### Что проверяет CI:
1. ✅ Установка Python 3.12
2. ✅ Установка зависимостей через uv
3. ✅ Запуск всех тестов
4. ✅ Проверка покрытия >= 95%
5. ✅ Генерация отчета о покрытии

## Особенности тестов

### Все тесты используют моки
- **Не требуется реальная БД** - все операции с БД замокированы
- **Быстрое выполнение** - все тесты выполняются за < 1 секунду
- **Изоляция** - каждый тест независим от других

## Troubleshooting

### Ошибка "ModuleNotFoundError: No module named 'shop_api'"

Убедитесь, что установлен `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/your/project/hw2/hw
```

### Тесты не находятся

Запускайте pytest из корневой директории проекта (`hw2/hw/`).
