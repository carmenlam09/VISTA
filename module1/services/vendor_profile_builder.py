import re
from typing import Any
from models.vendor import VendorProfile


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
    profile = VendorProfile()
    for data in extractions:
        for key in ("vendor_name", "registration_number", "country", "address"):
            if not getattr(profile, key) and data.get(key):
                setattr(profile, key, _clean(data[key]))
        profile.directors.extend(data.get("directors", []))
        profile.shareholders.extend(data.get("shareholders", []))
        profile.ubo.extend(data.get("ubo", []))
        profile.related_parties.extend(data.get("related_parties", []))
    profile.directors = _dedupe(profile.directors, "director_name")
    profile.shareholders = _dedupe(profile.shareholders, "shareholder_name")
    profile.ubo = _dedupe(profile.ubo, "ubo_name")
    profile.related_parties = _dedupe(profile.related_parties, "related_party_name")
    return profile
