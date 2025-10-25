from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# чтобы импорты shop_api.* были доступны при запуске alembic
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from shop_api.config import settings  # noqa
from shop_api.orm import Base  # noqa

# конфиг Alembic
config = context.config

# логирование
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Модель метаданных
target_metadata = Base.metadata

def get_url() -> str:
    # Берём строку подключения из настроек приложения (.env)
    return settings.sqlalchemy_url

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
