"""Loads and validates config/report_template.yaml into a
ReportTemplateConfig. Mirrors module3/app/taxonomy/loader.py and
module5/app/policy/loader.py."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.report_template import ReportTemplateConfig


class TemplateLoadError(Exception):
    """Raised when the report template config is missing or fails
    validation. The message is meant to be readable by whoever edited the
    YAML, not just engineers."""


def load_template(path: str | Path | None = None) -> ReportTemplateConfig:
    template_path = Path(path or settings.report_template_path)
    if not template_path.exists():
        raise TemplateLoadError(f"Report template config not found at {template_path}")

    try:
        raw = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TemplateLoadError(f"Report template config at {template_path} is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise TemplateLoadError(f"Report template config at {template_path} must be a YAML mapping at the top level")

    try:
        return ReportTemplateConfig.model_validate(raw)
    except ValidationError as exc:
        raise TemplateLoadError(f"Report template config at {template_path} failed validation:\n{exc}") from exc
