"""The keyword library / risk taxonomy contract.

This is what compliance/risk staff edit — config/taxonomy.yaml is loaded
into this shape by app/taxonomy/loader.py. Kept separate from
app/schemas/finding.py so the editable config format can change without
touching the stable Module 4-facing output schema.

Note: theme names here (`tax_offence`, etc.) are Module 3's own taxonomy,
not a reuse of Module 2's `RiskCategory` enum — Module 2's enum uses `tax`
where this uses `tax_offence`. They describe the same domain but are
independently config-driven per the spec, so keeping them decoupled avoids
a Python-level dependency between modules that run in separate venvs.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class RiskTheme(str, Enum):
    FINANCIAL_CRIME = "financial_crime"
    SANCTIONS = "sanctions"
    FRAUD = "fraud"
    REGULATORY_BREACH = "regulatory_breach"
    TAX_OFFENCE = "tax_offence"
    ESG = "esg"
    OPERATIONAL = "operational"


class KeywordEntry(BaseModel):
    phrase: str
    themes: list[RiskTheme]
    negation_guard: list[str] = Field(
        default_factory=list,
        description=(
            "Phrases that, when present in the same hit text as `phrase`, indicate the match does not "
            "represent risk-relevant wrongdoing by the entity itself — victim framing ('victim of'), "
            "exoneration ('cleared of'), or the entity being the plaintiff rather than defendant "
            "('filed by'). A match with a negation cue present is suppressed from findings, not kept "
            "as a positive risk signal."
        ),
    )
    notes: str | None = None

    @field_validator("phrase")
    @classmethod
    def _phrase_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("keyword phrase must not be blank")
        return value

    @field_validator("themes")
    @classmethod
    def _at_least_one_theme(cls, value: list[RiskTheme]) -> list[RiskTheme]:
        if not value:
            raise ValueError("a keyword must map to at least one risk theme")
        return value


class TaxonomyConfig(BaseModel):
    version: str
    themes: dict[RiskTheme, str]
    keywords: list[KeywordEntry]

    @field_validator("themes")
    @classmethod
    def _all_themes_described(cls, value: dict[RiskTheme, str]) -> dict[RiskTheme, str]:
        missing = set(RiskTheme) - set(value)
        if missing:
            raise ValueError(f"taxonomy is missing a description for: {sorted(m.value for m in missing)}")
        return value
