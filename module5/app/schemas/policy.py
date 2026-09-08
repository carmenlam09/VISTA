"""The KYV policy/governance rule library contract — config/policy_rules.yaml
is loaded into this shape by app/policy/loader.py. Mirrors Module 3's
taxonomy config pattern (keyword library -> YAML -> validated Pydantic
model), same audience: compliance/risk staff editing rules, not engineers
editing code.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}
DISPOSITION_ORDER = {"likely_false_positive": 0, "needs_review": 1, "high_priority_review": 2}


class RiskRating(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


RATING_ORDER = {RiskRating.LOW: 0, RiskRating.MEDIUM: 1, RiskRating.HIGH: 2}


class EDDLevel(str, Enum):
    STANDARD = "standard"
    ENHANCED = "enhanced"
    SENIOR_ESCALATION = "senior_escalation"


EDD_LEVEL_ORDER = {EDDLevel.STANDARD: 0, EDDLevel.ENHANCED: 1, EDDLevel.SENIOR_ESCALATION: 2}


class RuleMatchCriteria(BaseModel):
    themes: list[str] = Field(default_factory=list)  # empty = matches any theme
    min_severity: str | None = None  # "low" | "medium" | "high"; None = no severity floor
    min_confidence_score: int = 0
    min_disposition: str | None = None  # "needs_review" | "high_priority_review"; None = any
    entity_types: list[str] = Field(default_factory=list)  # empty = any entity type
    nationalities: list[str] = Field(default_factory=list)  # empty = any nationality

    @field_validator("min_severity")
    @classmethod
    def _valid_severity(cls, value: str | None) -> str | None:
        if value is not None and value not in SEVERITY_ORDER:
            raise ValueError(f"min_severity must be one of {list(SEVERITY_ORDER)}, got {value!r}")
        return value

    @field_validator("min_disposition")
    @classmethod
    def _valid_disposition(cls, value: str | None) -> str | None:
        if value is not None and value not in DISPOSITION_ORDER:
            raise ValueError(f"min_disposition must be one of {list(DISPOSITION_ORDER)}, got {value!r}")
        return value


class EDDRequirement(BaseModel):
    level: EDDLevel
    required_steps: list[str] = Field(default_factory=list)


class PolicyRule(BaseModel):
    rule_id: str
    description: str
    match: RuleMatchCriteria
    rating_contribution: RiskRating
    materiality_note: str
    edd: EDDRequirement

    @field_validator("rule_id")
    @classmethod
    def _rule_id_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("rule_id must not be blank")
        return value


class PolicyConfig(BaseModel):
    version: str
    rules: list[PolicyRule]

    @field_validator("rules")
    @classmethod
    def _unique_rule_ids(cls, value: list[PolicyRule]) -> list[PolicyRule]:
        ids = [r.rule_id for r in value]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ValueError(f"duplicate rule_id(s): {sorted(duplicates)}")
        return value
