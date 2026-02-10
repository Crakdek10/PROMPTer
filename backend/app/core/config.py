from __future__ import annotations
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "PROMPTer-backend"
    ENV: str = "dev"  # dev | prod | test
    LOG_LEVEL: str = "INFO"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # CORS (para Electron/Angular más adelante)
    CORS_ORIGINS: List[str] = []

    model_config = SettingsConfigDict(
        env_file="backend/.env",          # tu .env local (ignorado por git)
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
