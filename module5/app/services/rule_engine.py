"""Deterministic policy-rule evaluation — explicitly NOT LLM-driven, per the
spec ("this should be deterministic and testable, not left to the LLM"),
mirroring how Module 4 kept entity-resolution scoring deterministic.

`likely_false_positive` findings are excluded from rule matching entirely
(never trigger a rule) but the caller (assessment_engine.py) keeps their
finding_references visible in the draft's `excluded_findings` — never
silently dropped from the record.
"""

from dataclasses import dataclass

from app.schemas.entity import EntityProfile
from app.schemas.policy import DISPOSITION_ORDER, EDD_LEVEL_ORDER, RATING_ORDER, PolicyConfig, PolicyRule, RiskRating, SEVERITY_ORDER
from app.schemas.upstream import EnrichedFinding


@dataclass(frozen=True)
class RuleMatch:
    rule: PolicyRule
    triggering_finding_references: list[str]


@dataclass(frozen=True)
class CombinedAssessment:
    overall_risk_rating: RiskRating
    edd_level: str
    edd_required_steps: list[str]
    contributing_findings: list[str]


def split_excluded_findings(findings: list[EnrichedFinding]) -> tuple[list[EnrichedFinding], list[str]]:
    """Returns (survivors, excluded_finding_references). Survivors are
    everything Module 4 did NOT flag likely_false_positive."""
    survivors = [f for f in findings if f.triage.disposition_recommendation != "likely_false_positive"]
    excluded = [f.triage.finding_reference for f in findings if f.triage.disposition_recommendation == "likely_false_positive"]
    return survivors, excluded


def match_rules(survivors: list[EnrichedFinding], entity: EntityProfile, policy: PolicyConfig) -> list[RuleMatch]:
    results: list[RuleMatch] = []
    for rule in policy.rules:
        triggering = [f.triage.finding_reference for f in survivors if _finding_matches_rule(f, entity, rule)]
        if triggering:
            results.append(RuleMatch(rule=rule, triggering_finding_references=triggering))
    return results


def _finding_matches_rule(finding: EnrichedFinding, entity: EntityProfile, rule: PolicyRule) -> bool:
    criteria = rule.match

    if criteria.themes and not (set(criteria.themes) & set(finding.themes)):
        return False

    if criteria.min_severity is not None:
        severity = (finding.triage.finding_summary.severity or "").lower()
        if severity not in SEVERITY_ORDER or SEVERITY_ORDER[severity] < SEVERITY_ORDER[criteria.min_severity]:
            return False

    if finding.triage.confidence_score < criteria.min_confidence_score:
        return False

    if criteria.min_disposition is not None:
        disposition = finding.triage.disposition_recommendation
        if DISPOSITION_ORDER.get(disposition, -1) < DISPOSITION_ORDER[criteria.min_disposition]:
            return False

    if criteria.entity_types and entity.entity_type.value not in criteria.entity_types:
        return False

    if criteria.nationalities and (entity.nationality or "") not in criteria.nationalities:
        return False

    return True


def combine_rule_matches(matches: list[RuleMatch]) -> CombinedAssessment:
    """Overlapping rule matches combine to the HIGHEST rating/EDD level
    among them (never averaged or the first-match-wins) — a single strong
    rule should never be diluted by weaker ones also matching. Required
    steps are the deduplicated union across every matched rule, not just
    the rule(s) at the winning level, since a lower-tier rule's step can
    still be relevant context."""
    if not matches:
        return CombinedAssessment(
            overall_risk_rating=RiskRating.LOW, edd_level="standard", edd_required_steps=[], contributing_findings=[]
        )

    overall_rating = max((m.rule.rating_contribution for m in matches), key=lambda r: RATING_ORDER[r])
    overall_edd_level = max((m.rule.edd.level for m in matches), key=lambda level: EDD_LEVEL_ORDER[level])

    required_steps: list[str] = []
    for match in matches:
        for step in match.rule.edd.required_steps:
            if step not in required_steps:
                required_steps.append(step)

    contributing: list[str] = []
    for match in matches:
        for ref in match.triggering_finding_references:
            if ref not in contributing:
                contributing.append(ref)

    return CombinedAssessment(
        overall_risk_rating=overall_rating,
        edd_level=overall_edd_level.value,
        edd_required_steps=required_steps,
        contributing_findings=contributing,
    )
