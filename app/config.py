from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.7
    openai_max_tokens: Optional[int] = None
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "chatbot_db"
    app_title: str = "AI Chatbot API"
    app_version: str = "0.1.0"
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    class Config:
        env_file = ".env"


settings = Settings()
