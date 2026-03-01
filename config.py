# config.py

from pydantic import BaseSettings


class Settings(BaseSettings):
    ENV: str = "dev"
    DEBUG: bool = True
    APP_NAME: str = "AI Compliance Scanner"

    class Config:
        env_file = ".env"


settings = Settings()