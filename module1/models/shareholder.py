from dataclasses import dataclass


@dataclass
class Shareholder:
    shareholder_name: str
    ownership_percentage: float | None = None
