from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.routes._shared import record_to_report
from app.core.auth import Actor, get_current_actor, require_authorized
from app.db.session import get_db
from app.schemas.report import GeneratedReport, TraceabilityManifest
from app.services.audit_service import audit_service
from app.services.report_engine import report_engine

router = APIRouter(prefix="/api/entities/{entity_id}/report", tags=["report"])

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.get("", response_model=GeneratedReport)
async def get_report(
    entity_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> GeneratedReport:
    """Returns the latest generated report version, generating version 1 if
    none exists yet. Draft reports are sensitive — restricted to
    reviewer/approver/admin, same as Module 5's risk assessment drafts."""
    require_authorized(actor)

    existing = audit_service.get_latest_report(db, entity_id)
    if existing is not None:
        return record_to_report(existing)

    version = audit_service.next_version(db, entity_id)
    report = await report_engine.generate_report(entity_id, version)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    audit_service.save_report(db, report, actor.user_id)
    return report


@router.post("/regenerate", response_model=GeneratedReport)
async def regenerate_report(
    entity_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> GeneratedReport:
    """Always produces a NEW version — e.g. after a reviewer edits the
    Module 5 assessment — rather than overwriting the previous one."""
    require_authorized(actor)

    version = audit_service.next_version(db, entity_id)
    report = await report_engine.generate_report(entity_id, version)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    audit_service.save_report(db, report, actor.user_id)
    return report


@router.get("/{version}/download")
def download_report(
    entity_id: str,
    version: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> FileResponse:
    require_authorized(actor)
    record = audit_service.get_report(db, entity_id, version)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Report version {version} not found for entity '{entity_id}'")

    full_path = report_engine.output_dir / record.file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Report file is missing on disk")

    return FileResponse(str(full_path), filename=full_path.name, media_type=DOCX_MEDIA_TYPE)


@router.get("/{version}/manifest", response_model=TraceabilityManifest)
def get_manifest(
    entity_id: str,
    version: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> TraceabilityManifest:
    require_authorized(actor)
    record = audit_service.get_report(db, entity_id, version)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Report version {version} not found for entity '{entity_id}'")
    return TraceabilityManifest.model_validate(record.manifest)
