"""Pulls an entity's data from all five upstream modules into one unified
ReportData structure (capability 1). Every section is flagged explicitly —
`ok`, `missing` (upstream has nothing for this entity), or `error` (the
read itself failed) — so a reviewer always sees why a section is thin or
absent, rather than a silently blank or omitted section.
"""

from datetime import datetime, timezone

from app.schemas.entity import EntityProfile
from app.schemas.report_data import (
    AdverseMediaSection,
    EntityProfileSection,
    ReportData,
    RiskAssessmentSection,
    ScreeningEvidenceSection,
    SectionStatus,
    TriageSection,
)
from app.services.entity_lookup import EntityLookupService, entity_lookup_service
from app.services.module2_source import Module2Source, module2_source
from app.services.module3_source import Module3Source, module3_source
from app.services.module4_source import Module4Source, module4_source
from app.services.module5_source import Module5Source, module5_source


class ReportDataAggregator:
    def __init__(
        self,
        entity_lookup: EntityLookupService | None = None,
        m2_source: Module2Source | None = None,
        m3_source: Module3Source | None = None,
        m4_source: Module4Source | None = None,
        m5_source: Module5Source | None = None,
    ) -> None:
        self._entity_lookup = entity_lookup or entity_lookup_service
        self._module2_source = m2_source or module2_source
        self._module3_source = m3_source or module3_source
        self._module4_source = m4_source or module4_source
        self._module5_source = m5_source or module5_source

    async def aggregate(self, entity_id: str) -> ReportData | None:
        entity: EntityProfile | None = self._entity_lookup.get_entity(entity_id)
        if entity is None:
            return None

        entity_section = EntityProfileSection(status=SectionStatus.OK, profile=entity)

        screening_results = self._module2_source.get_results_for_entity(entity_id)
        screening_section = (
            ScreeningEvidenceSection(status=SectionStatus.OK, results=screening_results)
            if screening_results
            else ScreeningEvidenceSection(
                status=SectionStatus.MISSING, note="No Module 2 screening evidence found for this entity."
            )
        )

        adverse_findings = await self._module3_source.get_findings_for_entity(entity_id)
        adverse_section = (
            AdverseMediaSection(status=SectionStatus.OK, findings=adverse_findings)
            if adverse_findings
            else AdverseMediaSection(
                status=SectionStatus.MISSING, note="No Module 3 adverse media findings found for this entity."
            )
        )

        triage_results = self._module4_source.get_triage_results(entity_id)
        triage_section = (
            TriageSection(status=SectionStatus.OK, results=triage_results)
            if triage_results
            else TriageSection(status=SectionStatus.MISSING, note="No Module 4 triage results found for this entity.")
        )

        assessment = self._module5_source.get_assessment(entity_id)
        risk_section = (
            RiskAssessmentSection(status=SectionStatus.OK, assessment=assessment)
            if assessment is not None
            else RiskAssessmentSection(
                status=SectionStatus.MISSING, note="No Module 5 risk assessment found for this entity."
            )
        )

        return ReportData(
            entity_id=entity_id,
            entity=entity_section,
            screening_evidence=screening_section,
            adverse_media=adverse_section,
            triage=triage_section,
            risk_assessment=risk_section,
            aggregated_at=datetime.now(timezone.utc),
        )


report_data_aggregator = ReportDataAggregator()
