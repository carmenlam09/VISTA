from dataclasses import dataclass


@dataclass
class RelatedParty:
    related_party_name: str
    relationship_type: str = ""
