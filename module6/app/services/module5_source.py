"""Read-only adapter over Module 5's output.

Reads module5/database/risk_assessment.db directly as a plain SQLite file.
Critically, this reads the entity's single non-archived
`risk_assessment_drafts` row — which is Module 5's *current* state for that
entity, including any reviewer edits: Module 5's edit endpoint
(module5/app/services/audit_service.py `apply_edit`) mutates that same row
in place rather than inserting a new one, so `is_archived = 0` always means
"latest, including edits," never a stale first pass. This satisfies the
spec's hard requirement to use the reviewer-edited version when one exists,
without Module 6 needing any special-case logic for it.

Falls back to fixtures/*/sample_risk_assessments.json when the live
database is unavailable or has no row for this entity.
"""

import json
import sqlite3
from pathlib import Path

from app.core.config import settings
from app.schemas.upstream import RiskAssessmentDraftIn

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


def _load_fixture_assessment(fixtures_subdir: str, entity_id: str) -> RiskAssessmentDraftIn | None:
    path = FIXTURES_DIR / fixtures_subdir / "sample_risk_assessments.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data:
        if row["entity_id"] == entity_id:
            return RiskAssessmentDraftIn.model_validate(row)
    return None


def _read_live_assessment(db_path: Path, entity_id: str) -> RiskAssessmentDraftIn | None:
    if not db_path.exists():
        return None
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT id, draft_status, overall_risk_rating, matched_rules, materiality_justification,
                   edd_level, edd_required_steps, contributing_findings, excluded_findings,
                   generator, created_at
            FROM risk_assessment_drafts
            WHERE entity_id = ? AND is_archived = 0
            """,
            (entity_id,),
        ).fetchone()
    except sqlite3.DatabaseError:
        return None
    finally:
        conn.close()

    if row is None:
        return None

    return RiskAssessmentDraftIn(
        draft_id=row["id"],
        entity_id=entity_id,
        draft_status=row["draft_status"],
        overall_risk_rating=row["overall_risk_rating"],
        matched_rules=json.loads(row["matched_rules"]),
        materiality_justification=row["materiality_justification"],
        edd_recommendation={"level": row["edd_level"], "required_steps": json.loads(row["edd_required_steps"])},
        contributing_findings=json.loads(row["contributing_findings"]),
        excluded_findings=json.loads(row["excluded_findings"]),
        generator=row["generator"],
        created_at=row["created_at"],
    )


class Module5Source:
    def __init__(self, module5_db_path: str | None = None, fixtures_subdir: str = "complete") -> None:
        self._db_path = Path(module5_db_path or settings.module5_db_path)
        self._fixtures_subdir = fixtures_subdir

    def get_assessment(self, entity_id: str) -> RiskAssessmentDraftIn | None:
        live = _read_live_assessment(self._db_path, entity_id)
        if live is not None:
            return live
        return _load_fixture_assessment(self._fixtures_subdir, entity_id)


module5_source = Module5Source()
