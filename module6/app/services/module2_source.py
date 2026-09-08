"""Read-only adapter over Module 2's output — all five sources, since
Module 6 needs the full aggregated screening evidence for the report, not
just a subset. Reads module2/backend/database/screening.db directly as a
plain SQLite file, same pattern used at every module boundary in this repo.

Falls back to fixtures/*/sample_screening_results.json when the live
database is unavailable or has no rows for this entity.
"""

import json
import sqlite3
from pathlib import Path

from app.core.config import settings
from app.schemas.upstream import ScreeningResultIn

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


def _load_fixture_results(fixtures_subdir: str, entity_id: str) -> list[ScreeningResultIn]:
    path = FIXTURES_DIR / fixtures_subdir / "sample_screening_results.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ScreeningResultIn.model_validate(row) for row in data if row["entity_id"] == entity_id]


def _read_live_results(db_path: Path, entity_id: str) -> list[ScreeningResultIn]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, source, status, queried_at, hit_count, hits, source_metadata, error_message
            FROM screening_results
            WHERE entity_id = ? AND is_archived = 0
            ORDER BY source, queried_at DESC
            """,
            (entity_id,),
        ).fetchall()
    except sqlite3.DatabaseError:
        return []
    finally:
        conn.close()

    latest_per_source: dict[str, sqlite3.Row] = {}
    for row in rows:
        latest_per_source.setdefault(row["source"], row)

    return [
        ScreeningResultIn(
            result_id=row["id"],
            entity_id=entity_id,
            source=row["source"],
            status=row["status"],
            queried_at=row["queried_at"],
            hit_count=row["hit_count"],
            hits=json.loads(row["hits"]),
            source_metadata=json.loads(row["source_metadata"]),
            error_message=row["error_message"],
        )
        for row in latest_per_source.values()
    ]


class Module2Source:
    def __init__(self, module2_db_path: str | None = None, fixtures_subdir: str = "complete") -> None:
        self._db_path = Path(module2_db_path or settings.module2_db_path)
        self._fixtures_subdir = fixtures_subdir

    def get_results_for_entity(self, entity_id: str) -> list[ScreeningResultIn]:
        live = _read_live_results(self._db_path, entity_id)
        if live:
            return live
        return _load_fixture_results(self._fixtures_subdir, entity_id)


module2_source = Module2Source()
