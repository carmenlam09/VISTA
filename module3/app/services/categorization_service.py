"""AI-driven adverse media categorization. A distinct, swappable service from
the matching/filtering logic (mirroring Module 2's `SummaryGenerator`
pattern) so the prompt/model can be iterated on independently.

Real contextual judgment — is "fraud" in this headline about the entity
committing fraud or being its victim — is the LLM's job; the deterministic
fallback below only has the negation_guard heuristic already applied
upstream (see relevance_filter.find_keyword_matches) to work with, so it is
necessarily cruder. It exists so the engine works fully offline and in
tests, mirroring Module 1's Gemini-with-local-fallback and Module 2's
Anthropic-with-deterministic-fallback pattern.
"""

import json
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.core.config import settings
from app.schemas.adverse_news import AdverseNewsHitIn
from app.schemas.finding import AdverseMediaFinding, Confidence, Severity, SourceHitReference
from app.schemas.taxonomy import RiskTheme
from app.services.relevance_filter import KeywordMatch

SYSTEM_PROMPT = """You are an adverse media analyst assisting a bank's KYV (Know Your Vendor) screening team.

You are given one entity's name, one news hit (headline + excerpt) about that entity, and a list
of candidate taxonomy keyword matches already found in the text (each with the risk theme(s) it
maps to). Assess whether this hit represents a genuine adverse-risk signal FOR THE ENTITY ITSELF
— not, for example, the entity being a victim, whistleblower, plaintiff, or unrelated third party
mentioned in passing.

Respond with ONLY a JSON object of this exact shape, no prose before or after it:
{
  "findings": [
    {"themes": ["<financial_crime|sanctions|fraud|regulatory_breach|tax_offence|esg|operational>", ...],
     "severity": "<high|medium|low>",
     "confidence": "<high|medium|low>",
     "rationale": "<one sentence, must reference this specific hit's headline/excerpt content>",
     "matched_keywords": ["<keyword(s) from the candidate list this finding is based on>"]}
  ]
}

Hard rules:
- Only use themes from the candidate matches' themes, or themes clearly supported by the hit text.
- If the hit is about the entity being a victim, whistleblower, plaintiff, or is otherwise not a
  genuine risk signal for the entity, return an empty findings list — do not invent a finding to
  fill the response.
- Each finding's rationale must be specific to this hit — never a generic statement that could
  apply to any hit.
- Return zero findings if nothing in the candidate matches survives your contextual review.
"""


class AICategorizer(ABC):
    @abstractmethod
    async def categorize_hit(
        self,
        entity_id: str,
        legal_name: str,
        hit: AdverseNewsHitIn,
        source_result_id: str,
        candidate_matches: list[KeywordMatch],
    ) -> list[AdverseMediaFinding]:
        raise NotImplementedError


def _source_hit_reference(hit: AdverseNewsHitIn, result_id: str) -> SourceHitReference:
    return SourceHitReference(
        result_id=result_id,
        hit_id=hit.hit_id,
        headline=hit.headline,
        publication=hit.publication,
        publish_date=hit.publish_date,
        url=hit.url,
        excerpt=hit.excerpt,
    )


_HIGH_SEVERITY_THEMES = {RiskTheme.SANCTIONS, RiskTheme.FINANCIAL_CRIME, RiskTheme.FRAUD}


class DeterministicCategorizer(AICategorizer):
    """No network calls, no API key. Candidate matches already flagged
    `negated` by the upstream negation_guard heuristic are skipped here —
    this categorizer adds no further contextual judgment beyond that."""

    generator_name = "deterministic-fallback"

    async def categorize_hit(
        self,
        entity_id: str,
        legal_name: str,
        hit: AdverseNewsHitIn,
        source_result_id: str,
        candidate_matches: list[KeywordMatch],
    ) -> list[AdverseMediaFinding]:
        findings: list[AdverseMediaFinding] = []
        source_hit = _source_hit_reference(hit, source_result_id)

        for match in candidate_matches:
            if match.negated:
                continue
            severity = Severity.HIGH if any(t in _HIGH_SEVERITY_THEMES for t in match.themes) else Severity.MEDIUM
            rationale = f"Matched keyword '{match.phrase}' in \"{hit.headline}\": {hit.excerpt}"
            findings.append(
                AdverseMediaFinding(
                    finding_id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    themes=match.themes,
                    severity=severity,
                    confidence=Confidence.MEDIUM,
                    rationale=rationale,
                    matched_keywords=[match.phrase],
                    source_hit=source_hit,
                    generator=self.generator_name,
                    created_at=datetime.now(timezone.utc),
                )
            )
        return findings


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    match = _JSON_FENCE_RE.search(text)
    payload = match.group(1) if match else text
    return json.loads(payload)


class AnthropicCategorizer(AICategorizer):
    """Real LLM-backed categorizer. Falls back to `fallback` whenever no API
    key is configured, or the call/parse fails for any reason."""

    model = "claude-sonnet-5"

    def __init__(self, fallback: AICategorizer) -> None:
        self._fallback = fallback

    async def categorize_hit(
        self,
        entity_id: str,
        legal_name: str,
        hit: AdverseNewsHitIn,
        source_result_id: str,
        candidate_matches: list[KeywordMatch],
    ) -> list[AdverseMediaFinding]:
        if not settings.anthropic_api_key or not candidate_matches:
            return await self._fallback.categorize_hit(entity_id, legal_name, hit, source_result_id, candidate_matches)
        try:
            return await self._categorize_with_llm(entity_id, legal_name, hit, source_result_id, candidate_matches)
        except Exception:  # noqa: BLE001 — any failure degrades to the deterministic categorizer, never a crash
            return await self._fallback.categorize_hit(entity_id, legal_name, hit, source_result_id, candidate_matches)

    async def _categorize_with_llm(
        self,
        entity_id: str,
        legal_name: str,
        hit: AdverseNewsHitIn,
        source_result_id: str,
        candidate_matches: list[KeywordMatch],
    ) -> list[AdverseMediaFinding]:
        import anthropic  # imported lazily so the dependency is optional when no key is configured

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        payload = {
            "entity_name": legal_name,
            "hit": {"headline": hit.headline, "excerpt": hit.excerpt},
            "candidate_matches": [
                {"phrase": m.phrase, "themes": [t.value for t in m.themes], "negated": m.negated}
                for m in candidate_matches
            ],
        }
        message = client.messages.create(
            model=self.model,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        raw_text = "".join(block.text for block in message.content if block.type == "text")
        parsed = _extract_json(raw_text)

        source_hit = _source_hit_reference(hit, source_result_id)
        findings: list[AdverseMediaFinding] = []
        for raw_finding in parsed.get("findings", []):
            try:
                findings.append(
                    AdverseMediaFinding(
                        finding_id=str(uuid.uuid4()),
                        entity_id=entity_id,
                        themes=[RiskTheme(t) for t in raw_finding["themes"]],
                        severity=Severity(raw_finding["severity"]),
                        confidence=Confidence(raw_finding["confidence"]),
                        rationale=str(raw_finding["rationale"]),
                        matched_keywords=[str(k) for k in raw_finding.get("matched_keywords", [])],
                        source_hit=source_hit,
                        generator=f"anthropic:{self.model}",
                        created_at=datetime.now(timezone.utc),
                    )
                )
            except (KeyError, ValueError):
                continue  # skip a malformed finding rather than fail the whole hit
        return findings


categorizer: AICategorizer = AnthropicCategorizer(fallback=DeterministicCategorizer())
