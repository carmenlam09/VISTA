from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import Actor, get_current_actor
from app.db.session import get_db
from app.schemas.vendor import ExtractionMessage, ExtractionResponse, SaveVendorResponse, VendorProfile, VendorRecord, VendorSummary
from app.services.audit_service import audit_service
from app.services.docx_service import extract_docx_text
from app.services.entity_extractor import extract_entities
from app.services.ocr_service import extract_scanned_pdf_text
from app.services.pdf_service import extract_pdf_text
from app.services.vendor_profile_builder import build_vendor_profile
from app.services.vendor_service import get_vendor, save_vendor, search_vendors

router = APIRouter(prefix="/api/vendors", tags=["vendors"])


@router.post("/extract", response_model=ExtractionResponse)
async def extract(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> ExtractionResponse:
    """Extracts text from each uploaded file (native PDF, OCR fallback for
    scanned PDFs, docx, or plain text) and runs entity extraction on each,
    returning one consolidated, deduplicated draft profile — not yet saved."""
    extractions = []
    messages: list[ExtractionMessage] = []

    for file in files:
        content = await file.read()
        name = file.filename or "unknown"
        suffix = name.lower().rsplit(".", 1)[-1]
        if suffix == "pdf":
            text = extract_pdf_text(content) or extract_scanned_pdf_text(content)
        elif suffix == "docx":
            text = extract_docx_text(content)
        else:
            text = content.decode("utf-8", errors="replace")

        if not text.strip():
            messages.append(
                ExtractionMessage(
                    file_name=name,
                    message="No text could be extracted. Install OCR dependencies for scanned PDFs or verify the document.",
                    is_warning=True,
                )
            )
        else:
            messages.append(ExtractionMessage(file_name=name, message=f"Extracted {len(text):,} characters.", is_warning=False))
        extractions.append(extract_entities(text))

    profile = build_vendor_profile(extractions)
    audit_service.log(db, actor, "extraction", detail={"file_count": len(files), "file_names": [f.filename for f in files]})
    return ExtractionResponse(profile=profile, messages=messages, has_warnings=any(m.is_warning for m in messages))


@router.post("", response_model=SaveVendorResponse)
def create_vendor(
    profile: VendorProfile,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> SaveVendorResponse:
    if not profile.vendor_name.strip():
        raise HTTPException(status_code=400, detail="Vendor name is required.")
    vendor_id = save_vendor(db, profile)
    audit_service.log(db, actor, "save", vendor_id=vendor_id, detail={"vendor_name": profile.vendor_name})
    return SaveVendorResponse(vendor_id=vendor_id)


@router.get("", response_model=list[VendorSummary])
def list_vendors(
    query: str = "",
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> list[VendorSummary]:
    return search_vendors(db, query)


@router.get("/{vendor_id}", response_model=VendorRecord)
def read_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
) -> VendorRecord:
    vendor = get_vendor(db, vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
    audit_service.log(db, actor, "view", vendor_id=vendor_id)
    return vendor
