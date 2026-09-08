"""AI-driven materiality justification — a distinct, swappable service from
rule evaluation, consistent with the pattern in Modules 2-4.

Design note: the overall_risk_rating and edd_recommendation are NOT produced
by this service — they come from rule_engine.combine_rule_matches(),
deterministically. The spec's testing requirements explicitly want
"overlapping rule matches that should combine into a higher rating" to be a
property of "the rule-matching logic" (i.e. testable without an LLM in the
loop), so the LLM's job here is narrower than Module 4's reasoning step:
explain a rating/EDD that is already decided, not decide it. This is also
the more conservative choice for a governance-sensitive draft.

Mirrors Module 1's Gemini-with-local-fallback and Modules 2-4's
Anthropic-with-deterministic-fallback: with no ANTHROPIC_API_KEY configured,
or on any call/parse failure, falls back to a deterministic templated
narrative so the engine works fully offline and in tests.
"""

from abc import ABC, abstractmethod

from app.core.config import settings
from app.schemas.entity import EntityProfile
from app.services.rule_engine import CombinedAssessment, RuleMatch


class NarrativeService(ABC):
    @abstractmethod
    async def generate(
        self,
        entity: EntityProfile,
        matches: list[RuleMatch],
        combined: CombinedAssessment,
        excluded_findings: list[str],
    ) -> tuple[str, str]:
        """Returns (narrative, generator_name)."""
        raise NotImplementedError


class DeterministicNarrativeService(NarrativeService):
    generator_name = "deterministic-fallback"

    async def generate(
        self,
        entity: EntityProfile,
        matches: list[RuleMatch],
        combined: CombinedAssessment,
        excluded_findings: list[str],
    ) -> tuple[str, str]:
        if not matches:
            narrative = (
                f"No policy rules were triggered by {entity.legal_name}'s surviving findings. "
                f"Overall risk rating: {combined.overall_risk_rating.value}; standard due diligence applies."
            )
        else:
            lines = [
                f"{entity.legal_name}'s overall risk rating is {combined.overall_risk_rating.value}, "
                f"driven by {len(matches)} matched policy rule(s):"
            ]
            for match in matches:
                refs = ", ".join(match.triggering_finding_references)
                lines.append(
                    f"- {match.rule.rule_id} ({match.rule.rating_contribution.value} rating, "
                    f"{match.rule.edd.level.value} EDD): {match.rule.materiality_note.strip()} "
                    f"(triggered by: {refs})"
                )
            narrative = "\n".join(lines)

        if excluded_findings:
            narrative += (
                f"\n{len(excluded_findings)} likely-false-positive finding(s) were excluded from this rating "
                f"but remain visible in the record: {', '.join(excluded_findings)}."
            )

        return narrative, self.generator_name


SYSTEM_PROMPT = """You are a KYV (Know Your Vendor) risk assessment analyst assisting a bank's vendor risk team.

You are given an entity's name, a list of policy rules that ALREADY matched its screening findings
(each with a rule_id, description, materiality note, and the finding_reference(s) that triggered
it), the already-decided overall risk rating and EDD level those matches combined into, and any
findings excluded as likely false positives.

Write a short (2-5 sentence) materiality justification narrative explaining WHY the surviving
findings do or don't matter enough to affect the vendor relationship. You are explaining a decision
that has already been made by the deterministic rule engine — do not propose a different rating or
EDD level.

Hard rules:
- Cite specific rule_ids and finding_reference values from what you were given — never an
  unattributed or generic statement.
- Do not invent findings, rules, or citations not present in the input.
- If likely-false-positive findings were excluded, briefly acknowledge them as excluded-but-visible
  context, without letting them affect the stated rating.
- Return ONLY the narrative text, no JSON, no headers, no prose about your own process.
"""


class AnthropicNarrativeService(NarrativeService):
    model = "claude-sonnet-5"

    def __init__(self, fallback: NarrativeService) -> None:
        self._fallback = fallback

    async def generate(
        self,
        entity: EntityProfile,
        matches: list[RuleMatch],
        combined: CombinedAssessment,
        excluded_findings: list[str],
    ) -> tuple[str, str]:
        if not settings.anthropic_api_key:
            return await self._fallback.generate(entity, matches, combined, excluded_findings)
        try:
            return await self._generate_with_llm(entity, matches, combined, excluded_findings)
        except Exception:  # noqa: BLE001 — any failure degrades to the deterministic narrative, never a crash
            return await self._fallback.generate(entity, matches, combined, excluded_findings)

    async def _generate_with_llm(
        self,
        entity: EntityProfile,
        matches: list[RuleMatch],
        combined: CombinedAssessment,
        excluded_findings: list[str],
    ) -> tuple[str, str]:
        import anthropic  # imported lazily so the dependency is optional when no key is configured
        import json

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        payload = {
            "entity_name": entity.legal_name,
            "overall_risk_rating": combined.overall_risk_rating.value,
            "edd_level": combined.edd_level,
            "matched_rules": [
                {
                    "rule_id": m.rule.rule_id,
                    "description": m.rule.description,
                    "materiality_note": m.rule.materiality_note,
                    "rating_contribution": m.rule.rating_contribution.value,
                    "triggering_finding_references": m.triggering_finding_references,
                }
                for m in matches
            ],
            "excluded_findings": excluded_findings,
        }
        message = client.messages.create(
            model=self.model,
            max_tokens=700,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
        narrative = "".join(block.text for block in message.content if block.type == "text").strip()

        # Every rule_id given must be citable evidence the model actually used the input rather
        # than free-associating — if matches existed but none of their rule_ids appear anywhere
        # in the narrative, treat that as a failed generation and fall back.
        if matches and not any(m.rule.rule_id in narrative for m in matches):
            return await self._fallback.generate(entity, matches, combined, excluded_findings)
        if not narrative:
            return await self._fallback.generate(entity, matches, combined, excluded_findings)

        return narrative, f"anthropic:{self.model}"


narrative_service: NarrativeService = AnthropicNarrativeService(fallback=DeterministicNarrativeService())
