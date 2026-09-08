"""Orchestrates the full pipeline: aggregate Modules 1-5 -> draft narrative
-> generate the .docx -> build the traceability manifest. This is Module 6's
integration point (capability 6) — keep `generate_report` a clean,
UI-independent function. Version numbering is the caller's responsibility
(see audit_service.next_version) so this stays a pure generation step.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.schemas.report import GeneratedReport, ReportStatus
from app.schemas.report_data import SectionStatus
from app.services.document_generator import generate_document
from app.services.narrative_service import NarrativeService, narrative_service
from app.services.report_data_aggregator import ReportDataAggregator, report_data_aggregator
from app.services.template_loader import load_template
from app.services.traceability_service import build_manifest

_SECTION_STATUS_MAP = [
    ("entity_profile", "entity"),
    ("screening_findings_summary", "screening_evidence"),
    ("adverse_media_findings", "adverse_media"),
    ("triage_summary", "triage"),
    ("risk_assessment", "risk_assessment"),
]


class ReportEngine:
    def __init__(
        self,
        aggregator: ReportDataAggregator | None = None,
        narrator: NarrativeService | None = None,
        template_path: str | None = None,
        output_dir: str | None = None,
    ) -> None:
        self._aggregator = aggregator or report_data_aggregator
        self._narrator = narrator or narrative_service
        self._template = load_template(template_path)
        self._output_dir = Path(output_dir or settings.generated_reports_dir)

    @property
    def output_dir(self) -> Path:
        """The base directory report files are written under — routes that
        need to resolve a stored `file_path` (e.g. the download endpoint)
        must go through this rather than re-reading settings directly, so
        they stay correct if the engine's output_dir is ever overridden
        (as tests do) independently of the global config."""
        return self._output_dir

    async def generate_report(self, entity_id: str, version: int) -> GeneratedReport | None:
        data = await self._aggregator.aggregate(entity_id)
        if data is None:
            return None

        narrative = await self._narrator.generate(data.entity.profile, data)
        report_id = str(uuid.uuid4())
        manifest = build_manifest(entity_id, report_id, version, data)
        missing_sections = [
            section_id
            for section_id, attr in _SECTION_STATUS_MAP
            if getattr(data, attr).status != SectionStatus.OK
        ]

        output_path = self._output_dir / entity_id.replace(":", "_") / f"v{version}.docx"
        generate_document(self._template, data, narrative, report_id, version, ReportStatus.DRAFT.value, output_path)

        return GeneratedReport(
            report_id=report_id,
            entity_id=entity_id,
            version=version,
            status=ReportStatus.DRAFT,
            file_path=str(output_path.relative_to(self._output_dir)),
            narrative=narrative,
            manifest=manifest,
            missing_sections=missing_sections,
            generator=narrative.executive_summary.generator,
            created_at=datetime.now(timezone.utc),
        )


report_engine = ReportEngine()
