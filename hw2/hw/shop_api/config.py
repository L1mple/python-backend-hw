from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()  # загружаем .env, если есть

@dataclass(frozen=True)
class Settings:
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "shop")
    db_user: str = os.getenv("DB_USER", "shop")
    db_password: str = os.getenv("DB_PASSWORD", "shop")
    database_url: str | None = os.getenv("DATABASE_URL") or None

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        user = self.db_user
        pwd = self.db_password
        host = self.db_host
        port = self.db_port
        name = self.db_name
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}"

settings = Settings()
