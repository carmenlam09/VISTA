"""Read-only adapter over Module 2's output.

Reads module2/backend/database/screening.db directly as a plain SQLite file
— never Module 2's Python code, which runs in its own venv/process — and
returns the latest non-archived ScreeningResult row per source for an
entity, across all five sources. Same read-only, adapt-at-the-boundary
pattern Module 3 uses for the same database (module3/app/services/
adverse_news_source.py), generalized here to every source rather than just
adverse_news.

Falls back to fixtures/sample_screening_results.json when the live database
is unavailable or has no rows at all for this entity, so Module 4 runs and
tests fully standalone.
"""

import json
import sqlite3
from pathlib import Path

from app.core.config import settings
from app.schemas.upstream import ScreeningResultIn

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "sample_screening_results.json"


def _load_fixture_results(entity_id: str) -> list[ScreeningResultIn]:
    data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
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
        latest_per_source.setdefault(row["source"], row)  # first row per source wins: ORDER BY queried_at DESC

    results: list[ScreeningResultIn] = []
    for row in latest_per_source.values():
        results.append(
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
        )
    return results


class Module2Source:
    def __init__(self, module2_db_path: str | None = None) -> None:
        self._db_path = Path(module2_db_path or settings.module2_db_path)

    def get_results_for_entity(self, entity_id: str) -> list[ScreeningResultIn]:
        live = _read_live_results(self._db_path, entity_id)
        if live:
            return live
        return _load_fixture_results(entity_id)


module2_source = Module2Source()
