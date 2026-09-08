from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

MODULE5_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = MODULE5_DIR.parent


class Settings(BaseSettings):
    """Central configuration. All fields have safe defaults so the service
    runs fully on the deterministic fallback and bundled fixtures with no
    environment configured at all."""

    model_config = SettingsConfigDict(env_file=MODULE5_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(MODULE5_DIR / 'database' / 'risk_assessment.db').as_posix()}"
    module1_db_path: str = str(REPO_ROOT / "module1" / "database" / "vista.db")
    module2_db_path: str = str(REPO_ROOT / "module2" / "backend" / "database" / "screening.db")
    module4_db_path: str = str(REPO_ROOT / "module4" / "database" / "triage.db")
    module3_base_url: str = "http://localhost:8001"
    module3_timeout_seconds: float = 3.0
    policy_rules_path: str = str(MODULE5_DIR / "config" / "policy_rules.yaml")
    anthropic_api_key: str | None = None


settings = Settings()
