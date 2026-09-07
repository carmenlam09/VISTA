"""AI-generated screening summary. A distinct, swappable service from the
aggregation engine (per the spec) so the prompt/model can be iterated on
independently — anything downstream only depends on the SummaryGenerator
interface, not on how it's implemented.

Mirrors Module 1's real-API-with-local-fallback pattern: with no
ANTHROPIC_API_KEY configured (or on any call failure) this falls back to a
deterministic, rule-based summarizer built directly from the ScreeningResult
hits, so the feature works fully offline and in tests.
"""

import json
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.core.config import settings
from app.schemas.entity import EntityProfile
from app.schemas.screening import MatchConfidence, RiskCategory, ScreeningResult, SourceStatus
from app.schemas.summary import ScreeningSummary, SummaryFinding

SYSTEM_PROMPT = """You are a KYV (Know Your Vendor) screening analyst assisting a bank's vendor risk team.

You are given one entity profile and a set of ScreeningResult records, one per data source \
(ctos, netreveal, prior_kyv, adverse_news, public_records). Each result has a status \
(ok/error/timeout) and, when ok, zero or more hits.

Respond with ONLY a JSON object of this exact shape, no prose before or after it:
{
  "narrative": "2-4 sentence plain-language overview of the entity's screening posture",
  "findings": [
    {"theme": "<financial_crime|sanctions|fraud|regulatory_breach|tax|esg|operational>",
     "source": "<ctos|netreveal|prior_kyv|adverse_news|public_records>",
     "statement": "<one sentence describing the finding>",
     "severity": "<high|medium|low>"}
  ],
  "missing_or_inconclusive": ["<short note on a source that failed, or a hit too weak to act on>"]
}

Hard rules:
- Every finding cites exactly ONE source from the results you were given. Never merge hits from two
  sources into a single finding, and never state a finding without a source.
- Only summarize hits actually present in the given ScreeningResult records. Do not invent findings.
- If a source's status is not "ok", do not fabricate findings for it — note it under missing_or_inconclusive.
- A low-confidence hit should become a "low" severity finding, or move to missing_or_inconclusive if
  too weak to be actionable — never silently drop it.
"""


class SummaryGenerator(ABC):
    @abstractmethod
    async def generate(self, entity: EntityProfile, results: list[ScreeningResult]) -> ScreeningSummary:
        raise NotImplementedError


class DeterministicSummaryGenerator(SummaryGenerator):
    """No network calls, no API key — builds a summary directly from hits."""

    generator_name = "deterministic-fallback"

    async def generate(self, entity: EntityProfile, results: list[ScreeningResult]) -> ScreeningSummary:
        ok_results = [r for r in results if r.status == SourceStatus.OK]
        failed_results = [r for r in results if r.status != SourceStatus.OK]

        findings: list[SummaryFinding] = []
        for result in ok_results:
            for hit in result.hits:
                severity = {
                    MatchConfidence.HIGH: "high",
                    MatchConfidence.MEDIUM: "medium",
                    MatchConfidence.LOW: "low",
                }[hit.confidence]
                theme = hit.risk_categories[0] if hit.risk_categories else RiskCategory.OPERATIONAL
                findings.append(
                    SummaryFinding(
                        theme=theme,
                        source=result.source,
                        statement=f"{hit.title}: {hit.description}",
                        severity=severity,
                    )
                )

        missing = [
            f"{r.source.value} could not be queried ({r.error_message or r.status.value})" for r in failed_results
        ]
        total_hits = sum(r.hit_count for r in ok_results)

        if total_hits == 0:
            narrative = (
                f"No adverse findings were identified for {entity.legal_name} across "
                f"{len(ok_results)} of {len(results)} queried sources."
            )
        else:
            high_conf = sum(1 for f in findings if f.severity == "high")
            narrative = (
                f"{entity.legal_name} has {total_hits} finding(s) across {len(ok_results)} queried sources, "
                f"including {high_conf} high-confidence match(es). Review the per-source findings below "
                "before reaching a risk conclusion."
            )
        if failed_results:
            narrative += f" {len(failed_results)} source(s) could not be queried and are excluded from this summary."

        return ScreeningSummary(
            entity_id=entity.entity_id,
            narrative=narrative,
            findings=findings,
            missing_or_inconclusive=missing,
            generated_at=datetime.now(timezone.utc),
            generator=self.generator_name,
        )


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    match = _JSON_FENCE_RE.search(text)
    payload = match.group(1) if match else text
    return json.loads(payload)


class AnthropicSummaryGenerator(SummaryGenerator):
    """Real LLM-backed generator. Falls back to `fallback` whenever no API
    key is configured, or the call/parse fails for any reason — the reviewer
    always gets a summary, and it's always attributed correctly."""

    model = "claude-sonnet-5"

    def __init__(self, fallback: SummaryGenerator) -> None:
        self._fallback = fallback

    async def generate(self, entity: EntityProfile, results: list[ScreeningResult]) -> ScreeningSummary:
        if not settings.anthropic_api_key:
            return await self._fallback.generate(entity, results)
        try:
            return await self._generate_with_llm(entity, results)
        except Exception:  # noqa: BLE001 — any failure degrades to the deterministic summary, never a 500
            return await self._fallback.generate(entity, results)

    async def _generate_with_llm(self, entity: EntityProfile, results: list[ScreeningResult]) -> ScreeningSummary:
        import anthropic  # imported lazily so the dependency is optional when no key is configured

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        payload = {
            "entity": entity.model_dump(mode="json"),
            "results": [r.model_dump(mode="json") for r in results],
        }
        message = client.messages.create(
            model=self.model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        raw_text = "".join(block.text for block in message.content if block.type == "text")
        parsed = _extract_json(raw_text)

        valid_sources = {r.source for r in results}
        findings: list[SummaryFinding] = []
        for raw_finding in parsed.get("findings", []):
            try:
                finding = SummaryFinding.model_validate(raw_finding)
            except Exception:  # noqa: BLE001 — skip a malformed finding rather than fail the whole summary
                continue
            if finding.source not in valid_sources:
                continue  # never let an unattributed/invalid-source claim through
            findings.append(finding)

        return ScreeningSummary(
            entity_id=entity.entity_id,
            narrative=str(parsed.get("narrative", "")),
            findings=findings,
            missing_or_inconclusive=[str(m) for m in parsed.get("missing_or_inconclusive", [])],
            generated_at=datetime.now(timezone.utc),
            generator=f"anthropic:{self.model}",
        )


summary_generator: SummaryGenerator = AnthropicSummaryGenerator(fallback=DeterministicSummaryGenerator())
