"""Read-only adapter over Module 2's output (and, transitively, Module 1's).

Reads module2/backend/database/screening.db directly as a plain SQLite file
— never Module 2's Python code, which runs in its own venv/process — and
picks out the latest non-archived adverse_news ScreeningResult row for an
entity. Module 2's `hits` column is stored as JSON with the shape defined in
module2/backend/app/schemas/screening.py (`ScreeningHit`): title/description/
hit_date/raw, not the headline/publication/url/excerpt shape the Module 3
prompt illustrates — see app/schemas/adverse_news.py for the field mapping.

Resolving an entity_id to a legal_name/aliases (needed for the relevance
filter) means going one hop further back to Module 1's SQLite file, the same
read-only, adapt-at-the-boundary pattern Module 2 uses. This intentionally
duplicates a small slice of Module 2's `EntityService` logic rather than
importing it — the two modules run in separate venvs/processes, and Module 1
has no API of its own to call instead.

If either database is unavailable, or the entity isn't found in it, falls
back to app/fixtures/sample_adverse_news.json so Module 3 runs and tests
fully standalone.
"""

import json
import sqlite3
from pathlib import Path

from app.core.config import settings
from app.schemas.adverse_news import AdverseNewsBundle, AdverseNewsHitIn

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "sample_adverse_news.json"

_ENTITY_TABLES = {
    "vendor": ("vendors", "vendor_id", "vendor_name"),
    "director": ("directors", "director_id", "director_name"),
    "shareholder": ("shareholders", "shareholder_id", "shareholder_name"),
    "ubo": ("ubos", "ubo_id", "ubo_name"),
}


def _resolve_entity_name(db_path: Path, entity_id: str) -> str | None:
    if ":" not in entity_id or not db_path.exists():
        return None
    entity_type, raw_id = entity_id.split(":", 1)
    table_info = _ENTITY_TABLES.get(entity_type)
    if table_info is None:
        return None
    table, id_col, name_col = table_info

    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        row = conn.execute(f"SELECT {name_col} FROM {table} WHERE {id_col} = ?", (raw_id,)).fetchone()  # noqa: S608 — table/column names come from the fixed _ENTITY_TABLES map, not user input
        return row[0] if row else None
    except sqlite3.DatabaseError:
        return None
    finally:
        conn.close()


def _read_latest_adverse_news_row(db_path: Path, entity_id: str) -> tuple[str, str, list[dict]] | None:
    """Returns (result_id, queried_at, hits) for the latest non-archived
    adverse_news ScreeningResult row, or None if not found."""
    if not db_path.exists():
        return None
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT id, queried_at, hits FROM screening_results
            WHERE entity_id = ? AND source = 'adverse_news' AND is_archived = 0 AND status = 'ok'
            ORDER BY queried_at DESC LIMIT 1
            """,
            (entity_id,),
        ).fetchone()
        if row is None:
            return None
        return row["id"], row["queried_at"], json.loads(row["hits"])
    except sqlite3.DatabaseError:
        return None
    finally:
        conn.close()


def _map_module2_hit(raw_hit: dict) -> AdverseNewsHitIn:
    raw_metadata = raw_hit.get("raw") or {}
    return AdverseNewsHitIn(
        hit_id=raw_hit["hit_id"],
        headline=raw_hit["title"],
        excerpt=raw_hit["description"],
        publish_date=raw_hit.get("hit_date"),
        publication=raw_metadata.get("outlet") or raw_metadata.get("publication"),
        url=raw_metadata.get("url"),
        source_confidence=raw_hit.get("confidence"),
    )


def _load_fixture_bundles() -> dict[str, AdverseNewsBundle]:
    data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return {row["entity_id"]: AdverseNewsBundle.model_validate(row) for row in data}


class AdverseNewsSource:
    def __init__(
        self,
        module2_db_path: str | None = None,
        module1_db_path: str | None = None,
    ) -> None:
        self._module2_db_path = Path(module2_db_path or settings.module2_db_path)
        self._module1_db_path = Path(module1_db_path or settings.module1_db_path)

    def get_bundle(self, entity_id: str) -> AdverseNewsBundle | None:
        live = self._read_live(entity_id)
        if live is not None:
            return live
        return _load_fixture_bundles().get(entity_id)

    def _read_live(self, entity_id: str) -> AdverseNewsBundle | None:
        row = _read_latest_adverse_news_row(self._module2_db_path, entity_id)
        if row is None:
            return None
        result_id, queried_at, raw_hits = row
        legal_name = _resolve_entity_name(self._module1_db_path, entity_id) or entity_id
        return AdverseNewsBundle(
            entity_id=entity_id,
            legal_name=legal_name,
            aliases=[],
            result_id=result_id,
            queried_at=queried_at,
            hits=[_map_module2_hit(h) for h in raw_hits],
        )


adverse_news_source = AdverseNewsSource()
