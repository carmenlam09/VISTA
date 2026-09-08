"""Loads and validates config/retention_policy.yaml into a
RetentionPolicyConfig. Mirrors module3/app/taxonomy/loader.py and
module5/app/policy/loader.py."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.retention import RetentionPolicyConfig


class RetentionPolicyLoadError(Exception):
    """Raised when the retention policy config is missing or fails
    validation. The message is meant to be readable by whoever edited the
    YAML, not just engineers."""


def load_retention_policy(path: str | Path | None = None) -> RetentionPolicyConfig:
    policy_path = Path(path or settings.retention_policy_path)
    if not policy_path.exists():
        raise RetentionPolicyLoadError(f"Retention policy config not found at {policy_path}")

    try:
        raw = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RetentionPolicyLoadError(f"Retention policy config at {policy_path} is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise RetentionPolicyLoadError(f"Retention policy config at {policy_path} must be a YAML mapping at the top level")

    try:
        return RetentionPolicyConfig.model_validate(raw)
    except ValidationError as exc:
        raise RetentionPolicyLoadError(f"Retention policy config at {policy_path} failed validation:\n{exc}") from exc
