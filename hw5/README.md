# ДЗ

1) Добиться 95% покрытия тестами вашей второй домашки - 1 балл

2) Настроить автозапуск этих тестов в CI, если вы подключали сторонюю БД, то можно посмотреть вот [сюда](https://dev.to/kashifsoofi/integration-test-postgres-using-github-actions-3lln), чтобы поддержать тесты с ней в CI. По итогу у вас должен получится зеленый пайплайн - оценивается в еще 2 балла.

## Полезные команды

Установка переменной окружения (для Windows PowerShell):

```powershell
$env:PYTHONPATH = "$PWD"
```

Запуск тестов с покрытием:

```bash
pytest --cov=shop_api/routers
```

## Текущее покрытие тестами

```
Name                              Stmts   Miss  Cover
-----------------------------------------------------
shop_api\__init__.py                  0      0   100%
shop_api\cart\contracts.py           15      0   100%
shop_api\cart\store\__init__.py       3      0   100%
shop_api\cart\store\models.py        18      0   100%
shop_api\cart\store\queries.py       56      0   100%
shop_api\cart\store\schemas.py       13      0   100%
shop_api\db.py                       13      0   100%
shop_api\item\contracts.py           22      0   100%
shop_api\item\store\__init__.py       3      0   100%
shop_api\item\store\models.py        10      0   100%
shop_api\item\store\queries.py       53      1    98%
shop_api\item\store\schemas.py       18      0   100%
shop_api\main.py                     11      1    91%
shop_api\routers\cart.py             32      0   100%
shop_api\routers\item.py             42      0   100%
-----------------------------------------------------
TOTAL                               309      2    99%
```
