"""The vendor profile schema — Module 1's external output contract.

Field names and shapes here are frozen to match what Module 1 has always
emitted (see the Phase A contract audit / module1/README.md "Alignment
refactor" section): `vendor_name`, `registration_number`, `country`,
`address`, `directors`, `shareholders`, `ubo`, `related_parties`, with each
nested item's field names unchanged. Modules 2-7 (transitively, via Module 2)
depend on this shape.

The one addition is `id_number` on Director/Shareholder/Ubo — previously
Module 1 had no column at all for an individual's NRIC/passport number
(only vendors had `registration_number`), which meant Module 4's `id_match`
entity-resolution signal could never be true for any individual. This is
purely additive: existing consumers reading named columns are unaffected,
and the field is optional (`None` when not captured).
"""

from pydantic import BaseModel, Field


class Director(BaseModel):
    director_name: str
    nationality: str = ""
    id_number: str | None = None


class Shareholder(BaseModel):
    shareholder_name: str
    ownership_percentage: float | None = None
    id_number: str | None = None


class Ubo(BaseModel):
    ubo_name: str
    ownership_percentage: float | None = None
    id_number: str | None = None


class RelatedParty(BaseModel):
    related_party_name: str
    relationship_type: str = ""


class VendorProfile(BaseModel):
    """The consolidated, deduplicated profile built from one or more
    extractions — what a reviewer validates and saves."""

    vendor_name: str = ""
    registration_number: str = ""
    country: str = ""
    address: str = ""
    directors: list[Director] = Field(default_factory=list)
    shareholders: list[Shareholder] = Field(default_factory=list)
    ubo: list[Ubo] = Field(default_factory=list)
    related_parties: list[RelatedParty] = Field(default_factory=list)


class DirectorRecord(Director):
    director_id: int
    vendor_id: int


class ShareholderRecord(Shareholder):
    shareholder_id: int
    vendor_id: int


class UboRecord(Ubo):
    ubo_id: int
    vendor_id: int


class RelatedPartyRecord(RelatedParty):
    related_party_id: int
    vendor_id: int


class VendorRecord(BaseModel):
    """The persisted-and-read-back shape — what Module 2 (and, transitively,
    Modules 3-7) actually consumes from module1/database/vista.db."""

    vendor_id: int
    vendor_name: str
    registration_number: str | None = None
    country: str | None = None
    address: str | None = None
    created_date: str
    directors: list[DirectorRecord] = Field(default_factory=list)
    shareholders: list[ShareholderRecord] = Field(default_factory=list)
    ubo: list[UboRecord] = Field(default_factory=list)
    related_parties: list[RelatedPartyRecord] = Field(default_factory=list)


class VendorSummary(BaseModel):
    """One row of a search result — matches the columns `search_vendors`
    has always returned."""

    vendor_id: int
    vendor_name: str
    registration_number: str | None = None
    country: str | None = None
    address: str | None = None
    created_date: str


class ExtractionMessage(BaseModel):
    file_name: str
    message: str
    is_warning: bool


class ExtractionResponse(BaseModel):
    profile: VendorProfile
    messages: list[ExtractionMessage] = Field(default_factory=list)
    has_warnings: bool = False


class SaveVendorResponse(BaseModel):
    vendor_id: int
