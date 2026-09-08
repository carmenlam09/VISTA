"""The retention/archival policy config contract — config/retention_policy.yaml
is loaded into this shape by app/policy/loader.py. Mirrors Module 3's
taxonomy and Module 5's policy-rule config pattern: compliance/risk staff
edit the YAML, not code.

PLACEHOLDER VALUES — see the prominent warning in module7/README.md and in
the YAML file's own header comment. `is_placeholder` is carried through into
every retrieval response's disclaimer so it can't be missed downstream.
"""

from pydantic import BaseModel, Field, field_validator

from app.schemas.record import RecordType


class RetentionRule(BaseModel):
    retain_days: int = Field(gt=0)


class RetentionPolicyConfig(BaseModel):
    version: str
    is_placeholder: bool = True
    default_retain_days: int = Field(gt=0)
    record_types: dict[RecordType, RetentionRule] = Field(default_factory=dict)

    @field_validator("record_types")
    @classmethod
    def _all_record_types_covered(cls, value: dict) -> dict:
        missing = set(RecordType) - set(value)
        if missing:
            raise ValueError(f"retention policy is missing rule(s) for: {sorted(m.value for m in missing)}")
        return value

    def retain_days_for(self, record_type: RecordType) -> int:
        rule = self.record_types.get(record_type)
        return rule.retain_days if rule else self.default_retain_days
