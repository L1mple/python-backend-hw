from pydantic import Field
from pydantic_settings import SettingsConfigDict, BaseSettings



class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Server
    HOST: str = Field("0.0.0.0")
    PORT: int = Field("8000")

    # Postgres
    POSTGRES_HOST: str = Field("0.0.0.0")
    POSTGRES_PORT: int = Field("5432")
    POSTGRES_USER: str = Field("postgres")
    POSTGRES_PASSWORD: str = Field("postgres")
    POSTGRES_DB: str = Field("postgres")

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()