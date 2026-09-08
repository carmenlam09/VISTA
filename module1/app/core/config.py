from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

MODULE1_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Central configuration. All fields have safe defaults so the service
    runs fully on the deterministic local extractor with no environment
    configured at all — matching every other module's pattern."""

    model_config = SettingsConfigDict(env_file=MODULE1_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(MODULE1_DIR / 'database' / 'vista.db').as_posix()}"
    gemini_api_key: str | None = None


settings = Settings()
