from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

MODULE3_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = MODULE3_DIR.parent


class Settings(BaseSettings):
    """Central configuration. All fields have safe defaults so the service
    runs fully on the deterministic fallback and bundled fixtures with no
    environment configured at all."""

    model_config = SettingsConfigDict(env_file=MODULE3_DIR / ".env", extra="ignore")

    module2_db_path: str = str(REPO_ROOT / "module2" / "backend" / "database" / "screening.db")
    module1_db_path: str = str(REPO_ROOT / "module1" / "database" / "vista.db")
    taxonomy_path: str = str(MODULE3_DIR / "config" / "taxonomy.yaml")
    anthropic_api_key: str | None = None
    dedup_similarity_threshold: float = 0.3
    relevance_token_overlap_threshold: float = 0.5


settings = Settings()
