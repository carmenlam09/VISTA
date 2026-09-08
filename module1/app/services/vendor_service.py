"""Vendor persistence — replaces the pre-refactor database_service.py's raw
sqlite3 with SQLAlchemy, preserving the exact same query semantics: search
matches vendor_name OR registration_number by substring, ordered by
created_date descending; a director/shareholder/UBO/related-party entry
with a blank name is silently skipped (never persisted), matching the
original behavior exactly.
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.vendor import Director, RelatedParty, Shareholder, Ubo, Vendor
from app.schemas.vendor import (
    DirectorRecord,
    RelatedPartyRecord,
    ShareholderRecord,
    UboRecord,
    VendorProfile,
    VendorRecord,
    VendorSummary,
)


def save_vendor(db: Session, profile: VendorProfile) -> int:
    vendor = Vendor(
        vendor_name=profile.vendor_name,
        registration_number=profile.registration_number or None,
        country=profile.country or None,
        address=profile.address or None,
    )
    for director in profile.directors:
        if director.director_name:
            vendor.directors.append(
                Director(director_name=director.director_name, nationality=director.nationality or "", id_number=director.id_number)
            )
    for shareholder in profile.shareholders:
        if shareholder.shareholder_name:
            vendor.shareholders.append(
                Shareholder(
                    shareholder_name=shareholder.shareholder_name,
                    ownership_percentage=shareholder.ownership_percentage,
                    id_number=shareholder.id_number,
                )
            )
    for ubo in profile.ubo:
        if ubo.ubo_name:
            vendor.ubos.append(Ubo(ubo_name=ubo.ubo_name, ownership_percentage=ubo.ownership_percentage, id_number=ubo.id_number))
    for related_party in profile.related_parties:
        if related_party.related_party_name:
            vendor.related_parties.append(
                RelatedParty(related_party_name=related_party.related_party_name, relationship_type=related_party.relationship_type or "")
            )

    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor.vendor_id


def search_vendors(db: Session, query: str = "") -> list[VendorSummary]:
    pattern = f"%{query}%"
    vendors = (
        db.query(Vendor)
        .filter(or_(Vendor.vendor_name.like(pattern), Vendor.registration_number.like(pattern)))
        .order_by(Vendor.created_date.desc())
        .all()
    )
    return [
        VendorSummary(
            vendor_id=v.vendor_id,
            vendor_name=v.vendor_name,
            registration_number=v.registration_number,
            country=v.country,
            address=v.address,
            created_date=v.created_date,
        )
        for v in vendors
    ]


def get_vendor(db: Session, vendor_id: int) -> VendorRecord | None:
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if vendor is None:
        return None

    return VendorRecord(
        vendor_id=vendor.vendor_id,
        vendor_name=vendor.vendor_name,
        registration_number=vendor.registration_number,
        country=vendor.country,
        address=vendor.address,
        created_date=vendor.created_date,
        directors=[
            DirectorRecord(director_id=d.director_id, vendor_id=d.vendor_id, director_name=d.director_name, nationality=d.nationality or "", id_number=d.id_number)
            for d in sorted(vendor.directors, key=lambda item: item.director_id)
        ],
        shareholders=[
            ShareholderRecord(
                shareholder_id=s.shareholder_id, vendor_id=s.vendor_id, shareholder_name=s.shareholder_name,
                ownership_percentage=s.ownership_percentage, id_number=s.id_number,
            )
            for s in sorted(vendor.shareholders, key=lambda item: item.shareholder_id)
        ],
        ubo=[
            UboRecord(ubo_id=u.ubo_id, vendor_id=u.vendor_id, ubo_name=u.ubo_name, ownership_percentage=u.ownership_percentage, id_number=u.id_number)
            for u in sorted(vendor.ubos, key=lambda item: item.ubo_id)
        ],
        related_parties=[
            RelatedPartyRecord(
                related_party_id=r.related_party_id, vendor_id=r.vendor_id,
                related_party_name=r.related_party_name, relationship_type=r.relationship_type or "",
            )
            for r in sorted(vendor.related_parties, key=lambda item: item.related_party_id)
        ],
    )
