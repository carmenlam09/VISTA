from services.database_service import get_vendor


class UboRepository:
    def list_for_vendor(self, vendor_id: int) -> list[dict]:
        return (get_vendor(vendor_id) or {}).get("ubo", [])
