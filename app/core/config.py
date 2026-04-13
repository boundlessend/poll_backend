from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """настройки приложения"""

    app_name: str = "сервис опросов"
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/polls"
    )

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
