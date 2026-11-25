
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 60
    bcrypt_rounds: int = 12
    gemini_api_key: str = ""
    llm_model: str = "gemini-3.5-flash-lite"
    max_agent_steps: int = 6


settings = Settings()
