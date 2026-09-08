"""Read-only adapter over Module 1's output — Module 4's own copy of Module
2's EntityService (module2/backend/app/services/entity_service.py), not an
import of it. Reads module1/database/vista.db directly as a plain SQLite
file and adapts vendor/director/shareholder/UBO rows onto EntityProfile.

Falls back to fixtures/sample_entities.json when that database is
unavailable, so Module 4 runs and tests fully standalone. Also used to
resolve a *related* entity's legal_name (one hop, via `get_entity` again) —
that resolution feeds `entity_resolution.py`'s ownership/relationship
overlap scoring.
"""

import json
import sqlite3
from pathlib import Path

from app.core.config import settings
from app.schemas.entity import EntityProfile, EntityType, IdNumber, RelatedEntity

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "sample_entities.json"


def _load_fixture_entities() -> list[EntityProfile]:
    data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return [EntityProfile.model_validate(row) for row in data]


def _read_module1_entities(db_path: Path) -> list[EntityProfile]:
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        entities: list[EntityProfile] = []
        for vendor in conn.execute("SELECT * FROM vendors"):
            vendor_entity_id = f"vendor:{vendor['vendor_id']}"
            id_numbers = []
            if vendor["registration_number"]:
                id_numbers.append(IdNumber(type="SSM_NO", value=vendor["registration_number"]))
            vendor_related: list[RelatedEntity] = []

            for row in conn.execute(
                "SELECT director_id, director_name, nationality FROM directors WHERE vendor_id = ?",
                (vendor["vendor_id"],),
            ):
                sub_id = f"director:{row['director_id']}"
                vendor_related.append(RelatedEntity(entity_id=sub_id, relationship="has_director"))
                entities.append(
                    EntityProfile(
                        entity_id=sub_id,
                        entity_type=EntityType.DIRECTOR,
                        legal_name=row["director_name"],
                        nationality=row["nationality"] or None,
                        related_entities=[RelatedEntity(entity_id=vendor_entity_id, relationship="director_of")],
                    )
                )

            for row in conn.execute(
                "SELECT shareholder_id, shareholder_name FROM shareholders WHERE vendor_id = ?",
                (vendor["vendor_id"],),
            ):
                sub_id = f"shareholder:{row['shareholder_id']}"
                vendor_related.append(RelatedEntity(entity_id=sub_id, relationship="has_shareholder"))
                entities.append(
                    EntityProfile(
                        entity_id=sub_id,
                        entity_type=EntityType.SHAREHOLDER,
                        legal_name=row["shareholder_name"],
                        related_entities=[RelatedEntity(entity_id=vendor_entity_id, relationship="shareholder_of")],
                    )
                )

            for row in conn.execute(
                "SELECT ubo_id, ubo_name FROM ubos WHERE vendor_id = ?",
                (vendor["vendor_id"],),
            ):
                sub_id = f"ubo:{row['ubo_id']}"
                vendor_related.append(RelatedEntity(entity_id=sub_id, relationship="has_ubo"))
                entities.append(
                    EntityProfile(
                        entity_id=sub_id,
                        entity_type=EntityType.UBO,
                        legal_name=row["ubo_name"],
                        related_entities=[RelatedEntity(entity_id=vendor_entity_id, relationship="ubo_of")],
                    )
                )

            for row in conn.execute(
                "SELECT related_party_id, relationship_type FROM related_parties WHERE vendor_id = ?",
                (vendor["vendor_id"],),
            ):
                vendor_related.append(
                    RelatedEntity(
                        entity_id=f"related_party:{row['related_party_id']}",
                        relationship=row["relationship_type"] or "related_party",
                    )
                )

            entities.append(
                EntityProfile(
                    entity_id=vendor_entity_id,
                    entity_type=EntityType.VENDOR,
                    legal_name=vendor["vendor_name"],
                    id_numbers=id_numbers,
                    nationality=vendor["country"] or None,
                    related_entities=vendor_related,
                )
            )
        return entities
    finally:
        conn.close()


class EntityLookupService:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = Path(db_path or settings.module1_db_path)

    def list_entities(self) -> list[EntityProfile]:
        if self._db_path.exists():
            try:
                return _read_module1_entities(self._db_path)
            except sqlite3.DatabaseError:
                pass
        return _load_fixture_entities()

    def get_entity(self, entity_id: str) -> EntityProfile | None:
        for entity in self.list_entities():
            if entity.entity_id == entity_id:
                return entity
        return None

    def resolve_related_names(self, entity: EntityProfile) -> dict[str, str]:
        """Maps each of `entity`'s related_entities to its legal_name, where
        resolvable — used to check whether a finding's text corroborates
        relevance via a mention of a related party (director, shareholder,
        UBO) rather than the entity's own name."""
        names: dict[str, str] = {}
        for related in entity.related_entities:
            related_entity = self.get_entity(related.entity_id)
            if related_entity is not None:
                names[related.entity_id] = related_entity.legal_name
        return names


entity_lookup_service = EntityLookupService()
