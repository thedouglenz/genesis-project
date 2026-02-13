from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_APP_URL: str = "postgresql+asyncpg://localhost/genesis_app"
    DATABASE_TARGET_URL: str = "postgresql+asyncpg://localhost/genesis_target"
    LITELLM_PROXY_URL: str = "http://localhost:4000"
    LITELLM_API_KEY: str = ""
    AUTH_USERNAME: str = "admin"
    AUTH_PASSWORD: str = "admin"
    JWT_SECRET: str = "dev-secret-change-me"

    model_config = {"env_file": ".env"}


settings = Settings()
