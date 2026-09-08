"""Vendor Entity Profile — Module 4's own copy of the Module 1 -> Module 2
contract (module2/backend/app/schemas/entity.py), used the same way Module 2
uses it: as the shape `entity_lookup.py` adapts Module 1's raw rows into.
Not an import of Module 2's code — Module 4 runs in its own venv/process and
reads Module 1's database directly, the same boundary pattern Module 2 uses.
"""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    VENDOR = "vendor"
    DIRECTOR = "director"
    SHAREHOLDER = "shareholder"
    UBO = "ubo"


class IdNumber(BaseModel):
    type: str
    value: str


class RelatedEntity(BaseModel):
    entity_id: str
    relationship: str


class EntityProfile(BaseModel):
    entity_id: str
    entity_type: EntityType
    legal_name: str
    aliases: list[str] = Field(default_factory=list)
    id_numbers: list[IdNumber] = Field(default_factory=list)
    nationality: str | None = None
    date_of_incorporation_or_birth: date | None = None
    related_entities: list[RelatedEntity] = Field(default_factory=list)
