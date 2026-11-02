
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Enterprise Inventory Orchestrator"
    DATABASE_URL: str = "sqlite+aiosqlite:///./enterprise_inventory.db"
    API_KEY_SECRET: str = "super-secret-enterprise-key"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
