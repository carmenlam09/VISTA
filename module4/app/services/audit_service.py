"""Persists every triage run and every reviewer override — matching Module
2's audit_service.py pattern (module2/backend/app/services/audit_service.py).

"Every triage recommendation must be logged for audit purposes" is read
literally: each `run_triage` call persists a fresh batch of
TriageResultRecord rows, soft-archiving the entity's previous batch rather
than overwriting it, so the full history of what was recommended (and when)
survives. Overrides are a separate, append-only table — including overrides
of an already-archived recommendation, since a reviewer must always be able
to explain what they overrode.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.triage import TriageOverrideRecord, TriageResultRecord
from app.schemas.triage import OverrideRequest, TriageResult


class AuditService:
    def save_triage_batch(self, db: Session, entity_id: str, results: list[TriageResult]) -> None:
        db.query(TriageResultRecord).filter(
            TriageResultRecord.entity_id == entity_id,
            TriageResultRecord.is_archived.is_(False),
        ).update({"is_archived": True})

        for result in results:
            db.add(
                TriageResultRecord(
                    id=result.triage_id,
                    entity_id=result.entity_id,
                    finding_reference=result.finding_reference,
                    finding_source=result.finding_source.value,
                    finding_summary=result.finding_summary.model_dump(mode="json"),
                    match_quality=result.match_quality.model_dump(mode="json"),
                    historical_outcome_signal=result.historical_outcome_signal.model_dump(mode="json"),
                    confidence_score=result.confidence_score,
                    disposition_recommendation=result.disposition_recommendation.value,
                    rationale=result.rationale,
                    generator=result.generator,
                    is_archived=False,
                )
            )
        db.commit()

    def get_triage_record(self, db: Session, triage_id: str) -> TriageResultRecord | None:
        return db.query(TriageResultRecord).filter(TriageResultRecord.id == triage_id).first()

    def save_override(
        self,
        db: Session,
        actor_id: str,
        triage_record: TriageResultRecord,
        request: OverrideRequest,
    ) -> TriageOverrideRecord:
        override = TriageOverrideRecord(
            id=str(uuid.uuid4()),
            triage_id=triage_record.id,
            entity_id=triage_record.entity_id,
            finding_reference=triage_record.finding_reference,
            original_recommendation=triage_record.disposition_recommendation,
            original_confidence_score=triage_record.confidence_score,
            reviewer_decision=request.reviewer_decision.value,
            reviewer_notes=request.reviewer_notes,
            actor_id=actor_id,
        )
        db.add(override)
        db.commit()
        db.refresh(override)
        return override

    def list_overrides_for_entity(self, db: Session, entity_id: str) -> list[TriageOverrideRecord]:
        return (
            db.query(TriageOverrideRecord)
            .filter(TriageOverrideRecord.entity_id == entity_id)
            .order_by(TriageOverrideRecord.created_at.desc())
            .all()
        )


audit_service = AuditService()
