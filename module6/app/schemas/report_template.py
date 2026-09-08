"""The KYV report template contract — config/report_template.yaml is loaded
into this shape by app/services/template_loader.py. This is currently the
PLACEHOLDER template (see README) — swapping in the bank's real template
means replacing this file's content (and, if the section shape genuinely
differs, extending document_generator.py's rendering for a new section
`type`), without touching the aggregation/narrative/traceability layers.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SectionType(str, Enum):
    METADATA = "metadata"  # report/entity identifying details, no prose
    NARRATIVE = "narrative"  # AI-drafted prose paragraph(s)
    STRUCTURED = "structured"  # a labeled key/value block (e.g. entity profile fields)
    NARRATIVE_PLUS_TABLE = "narrative_plus_table"  # prose + a supporting data table
    TABLE = "table"  # a data table only, no prose
    NARRATIVE_PLUS_LIST = "narrative_plus_list"  # prose + a bulleted list (e.g. EDD steps)


class TemplateSection(BaseModel):
    section_id: str
    title: str
    type: SectionType

    @field_validator("section_id")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("section_id must not be blank")
        return value


class ReportTemplateConfig(BaseModel):
    version: str
    title: str
    is_placeholder: bool = True
    sections: list[TemplateSection] = Field(default_factory=list)

    @field_validator("sections")
    @classmethod
    def _unique_section_ids(cls, value: list[TemplateSection]) -> list[TemplateSection]:
        ids = [s.section_id for s in value]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ValueError(f"duplicate section_id(s): {sorted(duplicates)}")
        return value
