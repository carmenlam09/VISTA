"""Consolidates one or more raw extractions into a single, deduplicated
VendorProfile. Accumulation/dedup logic is byte-for-byte the same as the
pre-refactor version; the only change is validating into the Pydantic
VendorProfile at the end instead of a dataclass.

Note: the SSM shareholder extractor's transient `shares` field (raw share
count, distinct from `ownership_percentage`) is no longer carried into the
built profile. It was never part of the persisted contract either way — the
original `save_vendor` never wrote it to the database — so this only drops
it one step earlier, from the intermediate JSON a reviewer sees before
saving. See module1/README.md "Alignment refactor" section.
"""

import re
from typing import Any

from app.schemas.vendor import VendorProfile


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _dedupe(items: list[dict[str, Any]], name_key: str) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for item in items:
        name = _clean(item.get(name_key))
        marker = re.sub(r"[^a-z0-9]", "", name.lower())
        if name and marker not in seen:
            seen.add(marker)
            result.append({**item, name_key: name})
    return result


def build_vendor_profile(extractions: list[dict[str, Any]]) -> VendorProfile:
    merged: dict[str, Any] = {
        "vendor_name": "",
        "registration_number": "",
        "country": "",
        "address": "",
        "directors": [],
        "shareholders": [],
        "ubo": [],
        "related_parties": [],
    }
    for data in extractions:
        for key in ("vendor_name", "registration_number", "country", "address"):
            if not merged[key] and data.get(key):
                merged[key] = _clean(data[key])
        merged["directors"].extend(data.get("directors", []))
        merged["shareholders"].extend(data.get("shareholders", []))
        merged["ubo"].extend(data.get("ubo", []))
        merged["related_parties"].extend(data.get("related_parties", []))

    merged["directors"] = _dedupe(merged["directors"], "director_name")
    merged["shareholders"] = _dedupe(merged["shareholders"], "shareholder_name")
    merged["ubo"] = _dedupe(merged["ubo"], "ubo_name")
    merged["related_parties"] = _dedupe(merged["related_parties"], "related_party_name")

    return VendorProfile.model_validate(merged)
