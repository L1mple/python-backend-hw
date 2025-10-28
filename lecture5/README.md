# Lecture 5 - Тестирование

Этот проект содержит тесты для API магазина из lecture4.

## Структура проекта

```
lecture5/
├── tests/
│   ├── test_shop_api.py      # Основные тесты API
│   ├── requirements.txt      # Зависимости для тестов
│   └── README.md            # Документация тестов
├── requirements.txt          # Основные зависимости
├── pytest.ini              # Конфигурация pytest
├── Makefile                 # Команды для запуска тестов
├── run_tests.py            # Скрипт запуска тестов
└── demo_tests.py           # Демонстрация тестирования
```

## Установка

```bash
# Установка зависимостей
pip install -r requirements.txt
pip install -r tests/requirements.txt
pip install -e ../lecture4
```

## Запуск тестов

```bash
# Простой запуск
make test

# С покрытием кода
make test-cov

# Или через pytest
pytest tests/test_shop_api.py --cov=shop_api --cov-report=html
```

## Покрытие кода

Тесты обеспечивают покрытие кода не менее 95%.

## CI/CD

Тесты автоматически запускаются в GitHub Actions при каждом push и pull request.

## Что тестируется

- ✅ Создание товаров
- ✅ Получение товаров
- ✅ Обновление товаров
- ✅ Удаление товаров
- ✅ Создание корзин
- ✅ Добавление товаров в корзину
- ✅ Расчет стоимости корзины
- ✅ Фильтрация и пагинация
- ✅ Валидация данных
- ✅ Обработка ошибок
