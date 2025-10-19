# Пример работы с EdgeDB

Этот пример демонстрирует работу с **EdgeDB** (Gel)

## Что такое EdgeDB?

EdgeDB (Теперь называется Gel) - это база данных, построенная поверх PostgreSQL, которая предоставляет:

- **EdgeQL** - мощный язык запросов, похожий на GraphQL
- **Строгую типизацию** - схема определяется в `.gel` файлах
- **Автоматическую генерацию кода** - Python типы из схемы
- **Встроенные миграции** - автоматическое управление схемой
- **Объектно-ориентированные запросы** - работа с объектами, а не таблицами

## Установка и настройка:

### 1. Установка EdgeDB CLI
```bash
# macOS
curl --proto '=https' --tlsv1.2 -sSf https://sh.edgedb.com | sh

# Ubuntu/Debian
curl https://packages.edgedb.com/keys/edgedb.asc | sudo apt-key add -
echo "deb https://packages.edgedb.com/apt $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/edgedb.list
sudo apt update && sudo apt install edgedb-cli
```

### 2. Инициализация проекта
```bash
# Переход в папку с EdgeDB
cd 4_edgedb

# Инициализация проекта EdgeDB
edgedb project init

# Создание и применение миграций
edgedb migration create
edgedb migrate

# Установка Python зависимостей
pip install -r requirements.txt
```

### 3. Генерация типизированного Python кода
```bash
# Генерация асинхронных функций из queries/*.edgeql файлов
edgedb-py --target async --dir queries --out-dir generated

# Альтернативно - синхронные функции
edgedb-py --target sync --dir queries --out-dir generated

# Генерация в конкретный файл (все запросы в одном файле)
edgedb-py --target async --dir queries --file generated_queries.py
```

Вам сгенерируются Python функции, которые вы сможете вызывать из вашего кода. Они выполнят ваш запрос и вернут сразу Dataclass с результатом запроса, что довольно удобно. 


### Основные команды:

```bash
# Генерация асинхронных функций (рекомендуется)
edgedb-py --target async --dir queries --out-dir generated

# Генерация синхронных функций  
edgedb-py --target sync --dir queries --out-dir generated

# Генерация в один файл
edgedb-py --target async --dir queries --file all_queries.py

# Генерация с опциями
edgedb-py --target async \
          --dir queries \
          --out-dir generated \
          --no-skip-pyi-files  # Создавать .pyi файлы для type hints
```
