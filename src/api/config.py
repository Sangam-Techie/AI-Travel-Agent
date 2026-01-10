from pydantic_settings import BaseSettings  

class Settings(BaseSettings):
    """

    Application settings loaded from environment variables.

    These can be set in .env file or as environment variables.
    """
    # API settings
    app_name: str = "AI Travel Agent API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    # API keys (already in .env)
    groq_api_key: str
    amadeus_api_key: str
    amadeus_api_secret: str
    openweather_api_key: str

    # Agent Settings
    max_agent_iterations: int = 5
    agent_temperature: float = 0.7

    # Session Settings
    max_active_sessions: int = 100
    session_timeout_minutes: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()