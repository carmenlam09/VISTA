from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BACKEND_DIR.parent.parent


class Settings(BaseSettings):
    """Central configuration. All fields have safe defaults so the service
    runs fully on mocks/fallbacks with no environment configured at all."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'database' / 'screening.db').as_posix()}"
    module1_db_path: str = str(REPO_ROOT / "module1" / "database" / "vista.db")
    anthropic_api_key: str | None = None
    screening_cache_ttl_seconds: int = 3600
    connector_timeout_seconds: float = 5.0


settings = Settings()
