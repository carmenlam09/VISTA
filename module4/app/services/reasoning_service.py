"""AI contextual reasoning & confidence scoring — a distinct, swappable
service from entity-resolution scoring, consistent with Module 2's
`SummaryGenerator` and Module 3's `AICategorizer` pattern. Entity-resolution
sub-scores (name/nationality/ID/ownership) are already deterministic and
final by the time they reach here (per the spec, this service reasons OVER
those results, it does not recompute them) — its job is to combine them with
the historical signal and (for adverse-media findings) Module 3's
theme/severity into a confidence score, a disposition, and a rationale that
explicitly names which signals drove it.

Mirrors Module 1's Gemini-with-local-fallback and Module 2/3's
Anthropic-with-deterministic-fallback: with no ANTHROPIC_API_KEY configured,
or on any call/parse failure, falls back to a deterministic weighted-score
formula so the engine works fully offline and in tests.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import settings
from app.schemas.entity import EntityProfile
from app.schemas.triage import Disposition, FindingSummary, HistoricalOutcomeSignal, HistoricalPriorOutcome, MatchQuality


@dataclass(frozen=True)
class ReasoningResult:
    confidence_score: int
    disposition: Disposition
    rationale: str
    generator: str


class ReasoningService(ABC):
    @abstractmethod
    async def score(
        self,
        entity: EntityProfile,
        finding_summary: FindingSummary,
        match_quality: MatchQuality,
        historical_signal: HistoricalOutcomeSignal,
    ) -> ReasoningResult:
        raise NotImplementedError


# Deterministic weights. Tuned so a single strong structured signal (an
# exact ID match, or an escalated prior review) is enough to move a finding
# out of the "likely false positive" band, while name similarity alone
# — even a perfect one — is deliberately capped below the high-priority
# threshold on its own: a name match with no other corroboration is exactly
# the "common name" case a human should look at, not one this module should
# wave through as high priority by itself.
_NAME_WEIGHT = 45
_NATIONALITY_WEIGHT = 10
_ID_WEIGHT = 20
_OWNERSHIP_WEIGHT = 15
_SEVERITY_BONUS = {"high": 10, "medium": 5, "low": 0}
_HISTORICAL_BONUS = {
    HistoricalPriorOutcome.TRUE_HIT: 20,
    HistoricalPriorOutcome.FALSE_POSITIVE: -30,
    HistoricalPriorOutcome.UNKNOWN: 0,
}

HIGH_PRIORITY_THRESHOLD = 60
NEEDS_REVIEW_THRESHOLD = 35


def _disposition_for_score(score: int) -> Disposition:
    if score >= HIGH_PRIORITY_THRESHOLD:
        return Disposition.HIGH_PRIORITY_REVIEW
    if score >= NEEDS_REVIEW_THRESHOLD:
        return Disposition.NEEDS_REVIEW
    return Disposition.LIKELY_FALSE_POSITIVE


class DeterministicReasoningService(ReasoningService):
    generator_name = "deterministic-fallback"

    async def score(
        self,
        entity: EntityProfile,
        finding_summary: FindingSummary,
        match_quality: MatchQuality,
        historical_signal: HistoricalOutcomeSignal,
    ) -> ReasoningResult:
        raw_score = match_quality.name_similarity_score * _NAME_WEIGHT
        raw_score += _NATIONALITY_WEIGHT if match_quality.nationality_match else 0
        raw_score += _ID_WEIGHT if match_quality.id_match else 0
        raw_score += match_quality.ownership_overlap_score * _OWNERSHIP_WEIGHT
        raw_score += _SEVERITY_BONUS.get(_finding_severity(finding_summary), 0)
        raw_score += _HISTORICAL_BONUS[historical_signal.prior_outcome]

        confidence_score = max(0, min(100, round(raw_score)))
        disposition = _disposition_for_score(confidence_score)
        rationale = _build_rationale(entity, finding_summary, match_quality, historical_signal, confidence_score, disposition)

        return ReasoningResult(
            confidence_score=confidence_score,
            disposition=disposition,
            rationale=rationale,
            generator=self.generator_name,
        )


def _finding_severity(finding_summary: FindingSummary) -> str:
    return (finding_summary.severity or "").lower()


def _build_rationale(
    entity: EntityProfile,
    finding_summary: FindingSummary,
    match_quality: MatchQuality,
    historical_signal: HistoricalOutcomeSignal,
    confidence_score: int,
    disposition: Disposition,
) -> str:
    parts = [
        f"name similarity {round(match_quality.name_similarity_score * 100)}%"
        + (f" (matched '{match_quality.matched_name}')" if match_quality.matched_name else " (no match found)"),
        f"nationality {'matched' if match_quality.nationality_match else 'not corroborated'}",
        f"ID {'matched' if match_quality.id_match else 'not corroborated'}",
    ]
    if match_quality.ownership_overlap_score > 0:
        parts.append(
            f"ownership/relationship overlap {round(match_quality.ownership_overlap_score * 100)}% "
            f"(via {', '.join(match_quality.matched_related_entities)})"
        )
    else:
        parts.append("no ownership/relationship overlap found")

    if historical_signal.prior_review_found:
        parts.append(f"prior KYV review on record ({historical_signal.prior_outcome.value}: {historical_signal.prior_review_note})")
    else:
        parts.append("no prior KYV review found")

    signals = "; ".join(parts)
    return f"{signals} → confidence {confidence_score}/100, recommend {disposition.value}."


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    match = _JSON_FENCE_RE.search(text)
    payload = match.group(1) if match else text
    return json.loads(payload)


SYSTEM_PROMPT = """You are a KYV (Know Your Vendor) triage analyst assisting a bank's vendor risk team.

You are given an entity's profile, one screening finding about it, deterministic entity-resolution
sub-scores already computed for that finding (name similarity, nationality match, ID match,
ownership/relationship overlap), and a historical prior-review signal if one exists. You do NOT
recompute those sub-scores — they are given facts. Your job is to reason over them and produce a
final confidence score and triage recommendation, explaining your reasoning.

This module never makes a final decision — every output is a recommendation a human reviewer
confirms or overrides. Do not phrase your rationale as a conclusion; phrase it as a case for the
reviewer's attention.

Respond with ONLY a JSON object of this exact shape, no prose before or after it:
{
  "confidence_score": <integer 0-100>,
  "disposition_recommendation": "<likely_false_positive|needs_review|high_priority_review>",
  "rationale": "<one or two sentences, explicitly naming which of the given signals drove the score>"
}

Hard rules:
- The rationale must explicitly reference the specific signal values you were given (e.g. cite the
  actual name similarity percentage, whether nationality/ID matched, whether a prior review was
  found) — never a vague or generic statement.
- A single strong structured signal (an ID match, or an escalated/true-hit prior review) can justify
  high_priority_review even with modest name similarity. Conversely, a high name similarity with no
  other corroboration, especially a contradicted or missing nationality/ID match, should generally
  NOT be high_priority_review on its own — that is exactly the "common name" case a human needs to
  weigh, so prefer needs_review there rather than resolving it yourself.
"""


class AnthropicReasoningService(ReasoningService):
    model = "claude-sonnet-5"

    def __init__(self, fallback: ReasoningService) -> None:
        self._fallback = fallback

    async def score(
        self,
        entity: EntityProfile,
        finding_summary: FindingSummary,
        match_quality: MatchQuality,
        historical_signal: HistoricalOutcomeSignal,
    ) -> ReasoningResult:
        if not settings.anthropic_api_key:
            return await self._fallback.score(entity, finding_summary, match_quality, historical_signal)
        try:
            return await self._score_with_llm(entity, finding_summary, match_quality, historical_signal)
        except Exception:  # noqa: BLE001 — any failure degrades to the deterministic scorer, never a crash
            return await self._fallback.score(entity, finding_summary, match_quality, historical_signal)

    async def _score_with_llm(
        self,
        entity: EntityProfile,
        finding_summary: FindingSummary,
        match_quality: MatchQuality,
        historical_signal: HistoricalOutcomeSignal,
    ) -> ReasoningResult:
        import anthropic  # imported lazily so the dependency is optional when no key is configured

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        payload = {
            "entity_name": entity.legal_name,
            "finding": finding_summary.model_dump(mode="json"),
            "match_quality": match_quality.model_dump(mode="json"),
            "historical_signal": historical_signal.model_dump(mode="json"),
        }
        message = client.messages.create(
            model=self.model,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        raw_text = "".join(block.text for block in message.content if block.type == "text")
        parsed = _extract_json(raw_text)

        confidence_score = max(0, min(100, int(parsed["confidence_score"])))
        disposition = Disposition(parsed["disposition_recommendation"])
        rationale = str(parsed["rationale"])

        return ReasoningResult(
            confidence_score=confidence_score,
            disposition=disposition,
            rationale=rationale,
            generator=f"anthropic:{self.model}",
        )


reasoning_service: ReasoningService = AnthropicReasoningService(fallback=DeterministicReasoningService())
