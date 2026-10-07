"""Configuration management for the code review assistant."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    openai_api_key: str
    model_name: str = "gpt-4-turbo-preview"
    quality_threshold: int = 70
    max_retries: int = 3
    improvement_frequency: int = 5
    log_level: str = "INFO"

    # Directory paths
    data_dir: Path = Path("data")
    traces_dir: Path = Path("data/traces")
    improvements_dir: Path = Path("data/improvements")
    prompts_dir: Path = Path("data/prompts")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

# Ensure directories exist
settings.traces_dir.mkdir(parents=True, exist_ok=True)
settings.improvements_dir.mkdir(parents=True, exist_ok=True)
settings.prompts_dir.mkdir(parents=True, exist_ok=True)
