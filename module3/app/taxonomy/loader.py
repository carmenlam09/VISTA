"""Loads and validates config/taxonomy.yaml into a TaxonomyConfig."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.taxonomy import TaxonomyConfig


class TaxonomyLoadError(Exception):
    """Raised when the taxonomy config file is missing or fails validation —
    e.g. a keyword references an unknown theme, or a required theme has no
    description. The message is meant to be readable by whoever edited the
    YAML, not just engineers."""


def load_taxonomy(path: str | Path | None = None) -> TaxonomyConfig:
    taxonomy_path = Path(path or settings.taxonomy_path)
    if not taxonomy_path.exists():
        raise TaxonomyLoadError(f"Taxonomy config not found at {taxonomy_path}")

    try:
        raw = yaml.safe_load(taxonomy_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TaxonomyLoadError(f"Taxonomy config at {taxonomy_path} is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise TaxonomyLoadError(f"Taxonomy config at {taxonomy_path} must be a YAML mapping at the top level")

    try:
        return TaxonomyConfig.model_validate(raw)
    except ValidationError as exc:
        raise TaxonomyLoadError(f"Taxonomy config at {taxonomy_path} failed validation:\n{exc}") from exc
