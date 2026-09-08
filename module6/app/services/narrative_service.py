"""AI-drafted narrative sections (capability 2) — a distinct, swappable
service, consistent with the pattern in Modules 2, 3, and 5.

Two design choices worth calling out:

1. `risk_assessment_narrative` is NEVER LLM-authored, in either the
   Anthropic or deterministic path — it is always Module 5's own
   `materiality_justification` text, lightly wrapped. Per the spec: "Reuse
   Module 5's materiality justification as the basis... this module
   assembles and formats, it doesn't re-decide the assessment." Letting an
   LLM paraphrase that text risks silently dropping a citation Module 5
   already validated; reusing it verbatim is the only way to guarantee that
   can't happen.

2. Any section whose underlying ReportData is `missing`/`error` has its
   text forced to the deterministic "explicitly say so" text regardless of
   what the LLM produced for it — per the hard requirement that a missing
   section must never be silently glossed over. This is enforced in code,
   not just requested in the prompt, so it holds even if the model doesn't
   comply.

Mirrors Modules 1/2/3/5's real-API-with-deterministic-fallback pattern.
"""

import json
import re
from abc import ABC, abstractmethod

from app.core.config import settings
from app.schemas.entity import EntityProfile
from app.schemas.report import NarrativeSection, ReportNarrative
from app.schemas.report_data import ReportData, SectionStatus


class NarrativeService(ABC):
    @abstractmethod
    async def generate(self, entity: EntityProfile, data: ReportData) -> ReportNarrative:
        raise NotImplementedError


# --- Deterministic builders, one per section --------------------------


def _executive_summary(entity: EntityProfile, data: ReportData) -> str:
    parts = [f"This report summarizes KYV screening and risk assessment findings for {entity.legal_name} ({entity.entity_type.value})."]

    if data.risk_assessment.status == SectionStatus.OK:
        a = data.risk_assessment.assessment
        parts.append(
            f"The current risk assessment ({a.draft_status}) rates this entity as {a.overall_risk_rating} risk, "
            f"with an EDD recommendation of {a.edd_recommendation.level}."
        )
    else:
        parts.append(f"Risk assessment: {data.risk_assessment.note}")

    if data.screening_evidence.status == SectionStatus.OK:
        total_hits = sum(r.hit_count for r in data.screening_evidence.results)
        parts.append(f"Screening across {len(data.screening_evidence.results)} source(s) returned {total_hits} hit(s) in total.")
    else:
        parts.append(data.screening_evidence.note or "Screening evidence: not available.")

    if data.adverse_media.status == SectionStatus.OK:
        parts.append(f"{len(data.adverse_media.findings)} adverse media finding(s) were categorized.")
    else:
        parts.append(data.adverse_media.note or "Adverse media: not available.")

    if data.triage.status == SectionStatus.OK:
        high_priority = sum(1 for t in data.triage.results if t.disposition_recommendation == "high_priority_review")
        parts.append(f"Of {len(data.triage.results)} triaged finding(s), {high_priority} were flagged high priority for review.")
    else:
        parts.append(data.triage.note or "Triage: not available.")

    return " ".join(parts)


def _screening_findings_summary(data: ReportData) -> str:
    if data.screening_evidence.status != SectionStatus.OK:
        return data.screening_evidence.note or "No screening evidence available."
    lines = []
    for r in data.screening_evidence.results:
        if r.status == "ok":
            lines.append(f"{r.source}: {r.hit_count} hit(s)")
        else:
            lines.append(f"{r.source}: unavailable ({r.error_message or r.status})")
    return f"Screening evidence across {len(data.screening_evidence.results)} source(s): " + "; ".join(lines) + "."


def _adverse_media_narrative(data: ReportData) -> str:
    if data.adverse_media.status != SectionStatus.OK:
        return data.adverse_media.note or "No adverse media findings available."
    theme_counts: dict[str, int] = {}
    for finding in data.adverse_media.findings:
        for theme in finding.themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
    theme_summary = ", ".join(f"{theme} ({count})" for theme, count in theme_counts.items()) or "no themed findings"
    return f"{len(data.adverse_media.findings)} adverse media finding(s) were identified, spanning themes: {theme_summary}."


def _risk_assessment_narrative(data: ReportData) -> tuple[str, str]:
    """Returns (text, generator) — generator credits Module 5's own
    generator, not this module, since the text is reused verbatim."""
    if data.risk_assessment.status != SectionStatus.OK:
        return data.risk_assessment.note or "No risk assessment available.", "n/a"
    assessment = data.risk_assessment.assessment
    text = f"Overall risk rating: {assessment.overall_risk_rating}. {assessment.materiality_justification}"
    return text, f"module5-reuse:{assessment.generator}"


def _edd_recommendation_writeup(data: ReportData) -> str:
    if data.risk_assessment.status != SectionStatus.OK:
        return data.risk_assessment.note or "No EDD recommendation available."
    edd = data.risk_assessment.assessment.edd_recommendation
    steps = "; ".join(edd.required_steps) if edd.required_steps else "no additional steps specified"
    return f"Recommended EDD level: {edd.level}. Required steps: {steps}."


class DeterministicNarrativeService(NarrativeService):
    generator_name = "deterministic-fallback"

    async def generate(self, entity: EntityProfile, data: ReportData) -> ReportNarrative:
        risk_text, risk_generator = _risk_assessment_narrative(data)
        return ReportNarrative(
            executive_summary=NarrativeSection(
                section_id="executive_summary", title="Executive Summary",
                text=_executive_summary(entity, data), generator=self.generator_name,
            ),
            screening_findings_summary=NarrativeSection(
                section_id="screening_findings_summary", title="Screening Findings Summary",
                text=_screening_findings_summary(data), generator=self.generator_name,
            ),
            adverse_media_narrative=NarrativeSection(
                section_id="adverse_media_findings", title="Adverse Media Findings",
                text=_adverse_media_narrative(data), generator=self.generator_name,
            ),
            risk_assessment_narrative=NarrativeSection(
                section_id="risk_assessment", title="Risk Assessment & Materiality Justification",
                text=risk_text, generator=risk_generator,
            ),
            edd_recommendation_writeup=NarrativeSection(
                section_id="edd_recommendation", title="Enhanced Due Diligence (EDD) Recommendation",
                text=_edd_recommendation_writeup(data), generator=self.generator_name,
            ),
        )


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    match = _JSON_FENCE_RE.search(text)
    payload = match.group(1) if match else text
    return json.loads(payload)


SYSTEM_PROMPT = """You are a KYV (Know Your Vendor) report writer assisting a bank's vendor risk team.

You are given an entity's profile and its aggregated data across four upstream systems: raw
screening evidence, adverse media findings, triage results, and (separately, not for you to
narrate) a risk assessment. Draft three or four short, formal, audit-appropriate prose sections a
reviewer would otherwise write by hand.

Respond with ONLY a JSON object of this exact shape, no prose before or after it:
{
  "executive_summary": "<2-4 sentences>",
  "screening_findings_summary": "<2-4 sentences summarizing the raw screening evidence>",
  "adverse_media_narrative": "<2-4 sentences summarizing adverse media findings>",
  "edd_recommendation_writeup": "<2-3 sentences presenting the EDD recommendation>"
}

Hard rules:
- Only state facts present in the data you were given — counts, themes, sources, dispositions.
  Never invent a finding, a count, or a source that isn't in the input.
- If a section's underlying data says it is missing/unavailable, say so explicitly and plainly
  (e.g. "No adverse media findings were identified") — never omit the section or leave it vague.
- Do not draft a risk assessment narrative — that section is handled separately, using Module 5's
  own text directly.
- Formal, third-person, audit-appropriate tone throughout.
"""


class AnthropicNarrativeService(NarrativeService):
    model = "claude-sonnet-5"

    def __init__(self, fallback: NarrativeService) -> None:
        self._fallback = fallback

    async def generate(self, entity: EntityProfile, data: ReportData) -> ReportNarrative:
        fallback_narrative = await self._fallback.generate(entity, data)
        if not settings.anthropic_api_key:
            return fallback_narrative
        try:
            return await self._generate_with_llm(entity, data, fallback_narrative)
        except Exception:  # noqa: BLE001 — any failure degrades to the deterministic narrative, never a crash
            return fallback_narrative

    async def _generate_with_llm(
        self, entity: EntityProfile, data: ReportData, fallback_narrative: ReportNarrative
    ) -> ReportNarrative:
        import anthropic  # imported lazily so the dependency is optional when no key is configured

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        payload = {
            "entity": entity.model_dump(mode="json"),
            "screening_evidence": data.screening_evidence.model_dump(mode="json"),
            "adverse_media": data.adverse_media.model_dump(mode="json"),
            "triage": data.triage.model_dump(mode="json"),
        }
        message = client.messages.create(
            model=self.model,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        raw_text = "".join(block.text for block in message.content if block.type == "text")
        parsed = _extract_json(raw_text)

        def _section(key: str, section_id: str, title: str, data_status: SectionStatus, fallback: NarrativeSection) -> NarrativeSection:
            # A missing/error section is ALWAYS forced to the deterministic text — never trust the
            # LLM alone to have complied with "say so explicitly."
            if data_status != SectionStatus.OK:
                return fallback
            text = str(parsed.get(key, "")).strip()
            if not text:
                return fallback
            return NarrativeSection(section_id=section_id, title=title, text=text, generator=f"anthropic:{self.model}")

        return ReportNarrative(
            executive_summary=_section(
                "executive_summary", "executive_summary", "Executive Summary", SectionStatus.OK, fallback_narrative.executive_summary
            ),
            screening_findings_summary=_section(
                "screening_findings_summary", "screening_findings_summary", "Screening Findings Summary",
                data.screening_evidence.status, fallback_narrative.screening_findings_summary,
            ),
            adverse_media_narrative=_section(
                "adverse_media_narrative", "adverse_media_findings", "Adverse Media Findings",
                data.adverse_media.status, fallback_narrative.adverse_media_narrative,
            ),
            risk_assessment_narrative=fallback_narrative.risk_assessment_narrative,  # always reused verbatim, never LLM-authored
            edd_recommendation_writeup=_section(
                "edd_recommendation_writeup", "edd_recommendation", "Enhanced Due Diligence (EDD) Recommendation",
                data.risk_assessment.status, fallback_narrative.edd_recommendation_writeup,
            ),
        )


narrative_service: NarrativeService = AnthropicNarrativeService(fallback=DeterministicNarrativeService())
