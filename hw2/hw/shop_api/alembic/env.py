import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Добавляем путь к проекту для импорта моделей
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Импортируем Base и модели
# Импортируем напрямую из файлов, чтобы избежать циклических импортов
import importlib.util
spec = importlib.util.spec_from_file_location("database", os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.py"))
database_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database_module)
Base = database_module.Base

# Импортируем модели для регистрации в Base.metadata
spec_models = importlib.util.spec_from_file_location("db_models", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "db_models.py"))
models_module = importlib.util.module_from_spec(spec_models)
spec_models.loader.exec_module(models_module)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Получаем DATABASE_URL из переменной окружения
database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:admin@localhost:5432/shop_db")
# Alembic работает с синхронным драйвером, меняем asyncpg на psycopg2
database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Добавляем MetaData для autogenerate
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
