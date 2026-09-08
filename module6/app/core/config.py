from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

MODULE6_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = MODULE6_DIR.parent


class Settings(BaseSettings):
    """Central configuration. All fields have safe defaults so the service
    runs fully on the deterministic fallback and bundled fixtures with no
    environment configured at all."""

    model_config = SettingsConfigDict(env_file=MODULE6_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(MODULE6_DIR / 'database' / 'reports.db').as_posix()}"
    generated_reports_dir: str = str(MODULE6_DIR / "generated_reports")
    module1_db_path: str = str(REPO_ROOT / "module1" / "database" / "vista.db")
    module2_db_path: str = str(REPO_ROOT / "module2" / "backend" / "database" / "screening.db")
    module3_base_url: str = "http://localhost:8001"
    module3_timeout_seconds: float = 3.0
    module4_db_path: str = str(REPO_ROOT / "module4" / "database" / "triage.db")
    module5_db_path: str = str(REPO_ROOT / "module5" / "database" / "risk_assessment.db")
    report_template_path: str = str(MODULE6_DIR / "config" / "report_template.yaml")
    anthropic_api_key: str | None = None


settings = Settings()
