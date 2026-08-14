from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_host: str = Field(default="")
    database_port: int = Field(default=5432)
    database_name: str = Field(default="")
    database_user: str = Field(default="")
    database_password: str = Field(default="")

    cors_origins: str = Field(default="http://localhost:3000")

    @property
    def database_configured(self) -> bool:
        return bool(self.database_host and self.database_name and self.database_user)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
