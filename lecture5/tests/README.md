# Тесты для Shop API

Этот проект содержит тесты для API магазина из lecture4.

## Установка

```bash
pip install -r requirements.txt
pip install -r tests/requirements.txt
```

## Запуск тестов

```bash
# Запуск всех тестов
pytest

# Запуск с покрытием
pytest --cov=shop_api --cov-report=html

# Запуск конкретного теста
pytest tests/test_shop_api.py::test_create_item
```

## Покрытие кода

Тесты должны обеспечивать покрытие кода не менее 95%.

## CI/CD

Тесты автоматически запускаются в GitHub Actions при каждом push и pull request.