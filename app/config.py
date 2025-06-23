from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "chatbot_db"
    app_title: str = "AI Chatbot API"
    app_version: str = "0.1.0"

    class Config:
        env_file = ".env"


settings = Settings()
