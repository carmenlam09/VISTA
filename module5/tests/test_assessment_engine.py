"""End-to-end: fixture entities + Module 4-shaped fixture triage results ->
complete draft risk assessment, via the same AssessmentEngine the API route
uses. Runs entirely on the deterministic narrative fallback."""

from app.schemas.assessment import DraftStatus


async def test_no_rule_matches_yields_low_standard(fixture_assessment_engine):
    draft = await fixture_assessment_engine.run_assessment("vendor:fixture-nomatch")
    assert draft.overall_risk_rating.value == "low"
    assert draft.edd_recommendation.level.value == "standard"
    assert draft.matched_rules == []
    assert draft.draft_status == DraftStatus.AI_DRAFTED
    assert draft.label.startswith("AI-drafted")


async def test_single_rule_match(fixture_assessment_engine):
    draft = await fixture_assessment_engine.run_assessment("vendor:fixture-single")
    assert [m.rule_id for m in draft.matched_rules] == ["ESG-01"]
    assert draft.overall_risk_rating.value == "low"
    assert draft.contributing_findings == ["module3:finding-single-1"]


async def test_overlapping_rules_combine_to_high(fixture_assessment_engine):
    draft = await fixture_assessment_engine.run_assessment("vendor:fixture-overlap")
    assert set(m.rule_id for m in draft.matched_rules) == {"SANCTIONS-01", "SANCTIONS-02-HIGH-PRIORITY", "GENERAL-HIGH-CONFIDENCE-01"}
    assert draft.overall_risk_rating.value == "high"
    assert draft.edd_recommendation.level.value == "senior_escalation"


async def test_false_positive_excluded_but_visible(fixture_assessment_engine):
    draft = await fixture_assessment_engine.run_assessment("vendor:fixture-excluded")
    assert draft.excluded_findings == ["module2:ctos:fixture-result-excluded-ctos:hit-excluded-1"]
    assert draft.contributing_findings == ["module2:public_records:fixture-result-excluded-public:hit-excluded-2"]
    assert [m.rule_id for m in draft.matched_rules] == ["REGULATORY-BREACH-01"]
    assert draft.overall_risk_rating.value == "medium"


async def test_entity_attribute_gate_applies_rule_only_to_matching_entity_type(fixture_assessment_engine):
    """Identical finding shape (theme, disposition, confidence) on a vendor
    vs. a director — the vendor-scoped rule must apply to one and not the
    other, proving entity-attribute matching actually gates on entity_type."""
    vendor_draft = await fixture_assessment_engine.run_assessment("vendor:fixture-taxvendor")
    director_draft = await fixture_assessment_engine.run_assessment("director:fixture-taxdirector")

    assert [m.rule_id for m in vendor_draft.matched_rules] == ["TAX-OFFENCE-VENDOR-01"]
    assert vendor_draft.overall_risk_rating.value == "medium"

    assert director_draft.matched_rules == []
    assert director_draft.overall_risk_rating.value == "low"


async def test_unknown_entity_returns_none(fixture_assessment_engine):
    draft = await fixture_assessment_engine.run_assessment("vendor:does-not-exist")
    assert draft is None


async def test_every_matched_rule_carries_a_stable_contribution_string(fixture_assessment_engine):
    draft = await fixture_assessment_engine.run_assessment("vendor:fixture-overlap")
    for matched_rule in draft.matched_rules:
        assert matched_rule.contribution
        assert matched_rule.rule_id in {"SANCTIONS-01", "SANCTIONS-02-HIGH-PRIORITY", "GENERAL-HIGH-CONFIDENCE-01"}
