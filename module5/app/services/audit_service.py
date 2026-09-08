"""Persists every draft and every reviewer edit/approval — matching Module
2's and Module 4's audit_service.py pattern.

"Every draft, and every subsequent reviewer edit or override of it, must be
logged" is read literally: each `run_assessment` call persists a fresh
draft, soft-archiving the entity's previous one. `DraftHistoryRecord` is a
separate, append-only table covering the full lifecycle (drafted / edited /
approved) — including edits/approvals of an already-archived draft, since a
reviewer must always be able to explain what they changed and why.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.assessment import DraftHistoryRecord, RiskAssessmentDraftRecord
from app.schemas.assessment import DraftApprovalRequest, DraftEditRequest, DraftStatus, RiskAssessmentDraft


class AuditService:
    def save_draft(self, db: Session, draft: RiskAssessmentDraft, actor_id: str) -> None:
        db.query(RiskAssessmentDraftRecord).filter(
            RiskAssessmentDraftRecord.entity_id == draft.entity_id,
            RiskAssessmentDraftRecord.is_archived.is_(False),
        ).update({"is_archived": True})

        db.add(
            RiskAssessmentDraftRecord(
                id=draft.draft_id,
                entity_id=draft.entity_id,
                draft_status=draft.draft_status.value,
                overall_risk_rating=draft.overall_risk_rating.value,
                matched_rules=[m.model_dump(mode="json") for m in draft.matched_rules],
                materiality_justification=draft.materiality_justification,
                edd_level=draft.edd_recommendation.level.value,
                edd_required_steps=draft.edd_recommendation.required_steps,
                contributing_findings=draft.contributing_findings,
                excluded_findings=draft.excluded_findings,
                generator=draft.generator,
                is_archived=False,
            )
        )
        db.add(
            DraftHistoryRecord(
                id=str(uuid.uuid4()),
                draft_id=draft.draft_id,
                entity_id=draft.entity_id,
                action="drafted",
                actor_id=actor_id,
                changes={"overall_risk_rating": draft.overall_risk_rating.value, "edd_level": draft.edd_recommendation.level.value},
            )
        )
        db.commit()

    def get_draft(self, db: Session, draft_id: str) -> RiskAssessmentDraftRecord | None:
        return db.query(RiskAssessmentDraftRecord).filter(RiskAssessmentDraftRecord.id == draft_id).first()

    def apply_edit(
        self, db: Session, draft: RiskAssessmentDraftRecord, actor_id: str, request: DraftEditRequest
    ) -> RiskAssessmentDraftRecord:
        changes: dict = {}
        if request.overall_risk_rating is not None and request.overall_risk_rating.value != draft.overall_risk_rating:
            changes["overall_risk_rating"] = {"from": draft.overall_risk_rating, "to": request.overall_risk_rating.value}
            draft.overall_risk_rating = request.overall_risk_rating.value
        if request.edd_level is not None and request.edd_level.value != draft.edd_level:
            changes["edd_level"] = {"from": draft.edd_level, "to": request.edd_level.value}
            draft.edd_level = request.edd_level.value
        if request.edd_required_steps is not None:
            changes["edd_required_steps"] = {"from": draft.edd_required_steps, "to": request.edd_required_steps}
            draft.edd_required_steps = request.edd_required_steps
        if request.materiality_justification is not None:
            changes["materiality_justification"] = {"from": draft.materiality_justification, "to": request.materiality_justification}
            draft.materiality_justification = request.materiality_justification

        if changes and draft.draft_status != DraftStatus.APPROVED.value:
            draft.draft_status = DraftStatus.REVIEWER_EDITED.value

        db.add(
            DraftHistoryRecord(
                id=str(uuid.uuid4()),
                draft_id=draft.id,
                entity_id=draft.entity_id,
                action="edited",
                actor_id=actor_id,
                changes=changes,
                notes=request.edit_notes,
            )
        )
        db.commit()
        db.refresh(draft)
        return draft

    def approve(
        self, db: Session, draft: RiskAssessmentDraftRecord, actor_id: str, request: DraftApprovalRequest
    ) -> RiskAssessmentDraftRecord:
        draft.draft_status = DraftStatus.APPROVED.value
        db.add(
            DraftHistoryRecord(
                id=str(uuid.uuid4()),
                draft_id=draft.id,
                entity_id=draft.entity_id,
                action="approved",
                actor_id=actor_id,
                changes={"draft_status": DraftStatus.APPROVED.value},
                notes=request.approval_notes,
            )
        )
        db.commit()
        db.refresh(draft)
        return draft

    def list_history(self, db: Session, entity_id: str) -> list[DraftHistoryRecord]:
        return (
            db.query(DraftHistoryRecord)
            .filter(DraftHistoryRecord.entity_id == entity_id)
            .order_by(DraftHistoryRecord.created_at.desc())
            .all()
        )


audit_service = AuditService()
