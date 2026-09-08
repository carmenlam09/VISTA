from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

MODULE4_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = MODULE4_DIR.parent


class Settings(BaseSettings):
    """Central configuration. All fields have safe defaults so the service
    runs fully on the deterministic fallback and bundled fixtures with no
    environment configured at all."""

    model_config = SettingsConfigDict(env_file=MODULE4_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(MODULE4_DIR / 'database' / 'triage.db').as_posix()}"
    module1_db_path: str = str(REPO_ROOT / "module1" / "database" / "vista.db")
    module2_db_path: str = str(REPO_ROOT / "module2" / "backend" / "database" / "screening.db")
    module3_base_url: str = "http://localhost:8001"
    module3_timeout_seconds: float = 3.0
    anthropic_api_key: str | None = None


settings = Settings()
