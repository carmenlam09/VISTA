"""Read-only adapter over Module 4's output.

Reads module4/database/triage.db directly as a plain SQLite file — never
Module 4's Python code, which runs in its own venv/process — and returns
the entity's latest non-archived batch of triage results (one GET .../triage
call there persists a fresh batch and archives the previous one; this reads
whatever the most recent batch is). Same read-only, adapt-at-the-boundary
pattern used at every module boundary in this repo.

Falls back to fixtures/sample_triage_results.json when the live database is
unavailable or has no rows for this entity, so Module 5 runs and tests fully
standalone.
"""

import json
import sqlite3
from pathlib import Path

from app.core.config import settings
from app.schemas.upstream import TriageResultIn

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "sample_triage_results.json"


def _load_fixture_results(entity_id: str) -> list[TriageResultIn]:
    data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return [TriageResultIn.model_validate(row) for row in data if row["entity_id"] == entity_id]


def _read_live_results(db_path: Path, entity_id: str) -> list[TriageResultIn]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, finding_reference, finding_source, finding_summary, match_quality,
                   historical_outcome_signal, confidence_score, disposition_recommendation,
                   rationale, generator
            FROM triage_results
            WHERE entity_id = ? AND is_archived = 0
            """,
            (entity_id,),
        ).fetchall()
    except sqlite3.DatabaseError:
        return []
    finally:
        conn.close()

    return [
        TriageResultIn(
            triage_id=row["id"],
            entity_id=entity_id,
            finding_reference=row["finding_reference"],
            finding_source=row["finding_source"],
            finding_summary=json.loads(row["finding_summary"]),
            match_quality=json.loads(row["match_quality"]),
            historical_outcome_signal=json.loads(row["historical_outcome_signal"]),
            confidence_score=row["confidence_score"],
            disposition_recommendation=row["disposition_recommendation"],
            rationale=row["rationale"],
            generator=row["generator"],
        )
        for row in rows
    ]


class TriageSource:
    def __init__(self, module4_db_path: str | None = None) -> None:
        self._db_path = Path(module4_db_path or settings.module4_db_path)

    def get_triage_results(self, entity_id: str) -> list[TriageResultIn]:
        live = _read_live_results(self._db_path, entity_id)
        if live:
            return live
        return _load_fixture_results(entity_id)


triage_source = TriageSource()
