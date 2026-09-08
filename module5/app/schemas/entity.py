"""Vendor Entity Profile — Module 5's own copy of the Module 1 -> Module 2
contract, matching Module 2's and Module 4's copies of the same shape. Not
an import of another module's code — Module 5 runs in its own venv/process
and reads Module 1's database directly, the same boundary pattern used
throughout this repo.
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
