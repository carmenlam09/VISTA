"""Vendor Entity Profile — the Module 1 -> Module 2 contract.

Shape matches docs/VISTA_Module2_ClaudeCode_Prompt.md. Module 1's actual SQLite
schema (module1/database/schema.sql) predates this unified shape — it models
a vendor with nested directors/shareholders/UBOs rather than peer entities
with their own IDs — so `EntityService` (app/services/entity_service.py) adapts
Module 1's rows into this schema at read time. This file is the only place
that shape is defined; nothing here reaches back into Module 1's code.
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
