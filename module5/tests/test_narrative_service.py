from app.schemas.entity import EntityProfile, EntityType
from app.schemas.policy import EDDLevel, EDDRequirement, PolicyRule, RiskRating, RuleMatchCriteria
from app.services.narrative_service import DeterministicNarrativeService
from app.services.rule_engine import CombinedAssessment, RuleMatch

narrator = DeterministicNarrativeService()
ENTITY = EntityProfile(entity_id="vendor:1", entity_type=EntityType.VENDOR, legal_name="Example Corp")


def _rule(**overrides) -> PolicyRule:
    defaults = dict(
        rule_id="SANCTIONS-01",
        description="Sanctions theme finding",
        match=RuleMatchCriteria(themes=["sanctions"]),
        rating_contribution=RiskRating.HIGH,
        materiality_note="Sanctions exposure is materially significant.",
        edd=EDDRequirement(level=EDDLevel.SENIOR_ESCALATION, required_steps=["Escalate to MLRO"]),
    )
    defaults.update(overrides)
    return PolicyRule(**defaults)


async def test_no_matches_narrative_states_standard_dd():
    combined = CombinedAssessment(overall_risk_rating=RiskRating.LOW, edd_level="standard", edd_required_steps=[], contributing_findings=[])
    narrative, generator = await narrator.generate(ENTITY, [], combined, [])
    assert generator == "deterministic-fallback"
    assert "low" in narrative
    assert "standard" in narrative.lower() or "No policy rules" in narrative


async def test_narrative_cites_rule_id_and_finding_reference():
    rule = _rule()
    match = RuleMatch(rule=rule, triggering_finding_references=["module2:netreveal:r1:h1"])
    combined = CombinedAssessment(
        overall_risk_rating=RiskRating.HIGH, edd_level="senior_escalation", edd_required_steps=["Escalate to MLRO"],
        contributing_findings=["module2:netreveal:r1:h1"],
    )

    narrative, _ = await narrator.generate(ENTITY, [match], combined, [])

    assert rule.rule_id in narrative
    assert "module2:netreveal:r1:h1" in narrative
    assert "high" in narrative


async def test_narrative_acknowledges_excluded_findings_without_affecting_rating():
    rule = _rule()
    match = RuleMatch(rule=rule, triggering_finding_references=["module2:netreveal:r1:h1"])
    combined = CombinedAssessment(
        overall_risk_rating=RiskRating.HIGH, edd_level="senior_escalation", edd_required_steps=[],
        contributing_findings=["module2:netreveal:r1:h1"],
    )

    narrative, _ = await narrator.generate(ENTITY, [match], combined, ["module2:ctos:r9:h9"])

    assert "module2:ctos:r9:h9" in narrative
    assert "high" in narrative  # rating unaffected by the excluded finding
