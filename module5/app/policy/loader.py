"""Loads and validates config/policy_rules.yaml into a PolicyConfig.
Mirrors module3/app/taxonomy/loader.py."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.policy import PolicyConfig


class PolicyLoadError(Exception):
    """Raised when the policy rule config file is missing or fails
    validation — e.g. a duplicate rule_id, or an invalid min_severity value.
    The message is meant to be readable by whoever edited the YAML, not
    just engineers."""


def load_policy(path: str | Path | None = None) -> PolicyConfig:
    policy_path = Path(path or settings.policy_rules_path)
    if not policy_path.exists():
        raise PolicyLoadError(f"Policy rule config not found at {policy_path}")

    try:
        raw = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PolicyLoadError(f"Policy rule config at {policy_path} is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise PolicyLoadError(f"Policy rule config at {policy_path} must be a YAML mapping at the top level")

    try:
        return PolicyConfig.model_validate(raw)
    except ValidationError as exc:
        raise PolicyLoadError(f"Policy rule config at {policy_path} failed validation:\n{exc}") from exc
