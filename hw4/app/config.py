from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from tomlkit import item

BASE_DIR = Path(__file__).parent


class MongoConfig(BaseModel):
    url: str
    host: str
    port: int
    username: str
    password: str

    db_name: str = "mongo_db"
    pool_size: int = 100


class PrefixConfig(BaseModel):
    v1: str = ""
    api: str = ""


class AppConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.template", ".env"),
        case_sensitive=False,
        env_nested_delimiter="__",
    )

    app: AppConfig = AppConfig()
    prefix: PrefixConfig = PrefixConfig()
    mongo: MongoConfig


@lru_cache()
def get_settings() -> Settings:
    return Settings()
