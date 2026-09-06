from dataclasses import dataclass, field
from typing import Any


@dataclass
class VendorProfile:
    vendor_name: str = ""
    registration_number: str = ""
    country: str = ""
    address: str = ""
    directors: list[dict[str, Any]] = field(default_factory=list)
    shareholders: list[dict[str, Any]] = field(default_factory=list)
    ubo: list[dict[str, Any]] = field(default_factory=list)
    related_parties: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_name": self.vendor_name,
            "registration_number": self.registration_number,
            "country": self.country,
            "address": self.address,
            "directors": self.directors,
            "shareholders": self.shareholders,
            "ubo": self.ubo,
            "related_parties": self.related_parties,
        }
