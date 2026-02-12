from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Настройки сервера/приложения
    APP_TITLE: str = "Books API"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    APP_RELOAD: bool = True
    API_PREFIX: str = ""

    # Настройки БД
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "1234"
    DB_NAME: str = "books_db"
    DB_ECHO: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

settings = Settings()
