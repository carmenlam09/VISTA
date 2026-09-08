"""The Module 2 -> Module 3 input contract.

Module 2's real `ScreeningHit`/`ScreeningResult` shape
(module2/backend/app/schemas/screening.py) is `title`/`description`/`hit_date`/
`raw`, not the illustrative `headline`/`publication`/`url`/`excerpt` shape in
the Module 3 prompt. This schema maps onto what Module 2 actually produces:
`headline` <- `title`, `excerpt` <- `description`, `publish_date` <- `hit_date`,
and `publication`/`url` are read opportunistically from `raw` (Module 2's mock
adverse-news connector doesn't currently populate a `url`, so it's commonly
None — real connectors are expected to add one).

This is intentionally a plain Pydantic model defined here, not an import of
Module 2's code: Module 3 runs in its own venv/process and reads Module 2's
SQLite database directly (read-only), the same boundary pattern Module 2 uses
to read Module 1's output.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class AdverseNewsHitIn(BaseModel):
    hit_id: str
    headline: str
    excerpt: str
    publish_date: str | None = None
    publication: str | None = None
    url: str | None = None
    source_confidence: str | None = None  # Module 2's own match_confidence for this hit, informational


class AdverseNewsBundle(BaseModel):
    """One entity's adverse-news slice: the hits plus enough entity identity
    to run the relevance filter, from whichever source produced it (Module
    2's live DB or a standalone fixture file)."""

    entity_id: str
    legal_name: str
    aliases: list[str] = Field(default_factory=list)
    result_id: str
    queried_at: datetime
    hits: list[AdverseNewsHitIn] = Field(default_factory=list)
