from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Mortgage Eligibility Platform"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mortgage_db"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/mortgage_db"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # TrueLayer
    truelayer_client_id: str = ""
    truelayer_client_secret: str = ""
    truelayer_redirect_uri: str = "http://localhost:3000/banking/callback"
    truelayer_sandbox: bool = True

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # CORS
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
