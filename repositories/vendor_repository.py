from typing import Any
from services.database_service import get_vendor, save_vendor, search_vendors


class VendorRepository:
    def save(self, profile: dict[str, Any]) -> int:
        return save_vendor(profile)

    def search(self, query: str = "") -> list[dict[str, Any]]:
        return search_vendors(query)

    def get(self, vendor_id: int) -> dict[str, Any] | None:
        return get_vendor(vendor_id)
