"""Vendor Entity Profile — Module 6's own copy of the Module 1 -> Module 2
contract, matching every prior module's copy of the same shape. Not an
import of another module's code.
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
