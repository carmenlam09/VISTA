from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

MODULE7_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = MODULE7_DIR.parent


class Settings(BaseSettings):
    """Central configuration. All fields have safe defaults so the service
    runs fully on the local embedding provider and bundled fixtures with no
    environment configured at all."""

    model_config = SettingsConfigDict(env_file=MODULE7_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(MODULE7_DIR / 'database' / 'knowledge_repository.db').as_posix()}"
    retention_policy_path: str = str(MODULE7_DIR / "config" / "retention_policy.yaml")
    embedding_dimensions: int = 256


settings = Settings()
