from dataclasses import dataclass


@dataclass
class Ubo:
    ubo_name: str
    ownership_percentage: float | None = None
