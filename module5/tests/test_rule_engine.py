from app.schemas.entity import EntityProfile, EntityType
from app.schemas.policy import EDDLevel, EDDRequirement, PolicyConfig, PolicyRule, RiskRating, RuleMatchCriteria
from app.schemas.upstream import EnrichedFinding, TriageFindingSummaryIn, TriageResultIn
from app.services.rule_engine import combine_rule_matches, match_rules, split_excluded_findings

ENTITY = EntityProfile(entity_id="vendor:1", entity_type=EntityType.VENDOR, legal_name="Example Corp", nationality="Malaysia")


def _finding(**overrides) -> EnrichedFinding:
    triage_defaults = dict(
        triage_id="t1",
        entity_id="vendor:1",
        finding_reference="module2:ctos:r1:h1",
        finding_source="module2",
        finding_summary=TriageFindingSummaryIn(source="ctos", headline="H", excerpt="E", severity="medium"),
        confidence_score=50,
        disposition_recommendation="needs_review",
        rationale="r",
        generator="deterministic-fallback",
    )
    themes = overrides.pop("themes", [])
    triage_defaults.update(overrides)
    return EnrichedFinding(triage=TriageResultIn(**triage_defaults), themes=themes)


def _rule(**overrides) -> PolicyRule:
    defaults = dict(
        rule_id="RULE-1",
        description="test rule",
        match=RuleMatchCriteria(themes=["sanctions"]),
        rating_contribution=RiskRating.MEDIUM,
        materiality_note="note",
        edd=EDDRequirement(level=EDDLevel.ENHANCED, required_steps=["step 1"]),
    )
    defaults.update(overrides)
    return PolicyRule(**defaults)


def _policy(*rules: PolicyRule) -> PolicyConfig:
    return PolicyConfig(version="1.0", rules=list(rules))


# --- No match / single match / overlapping match -------------------------


def test_no_rules_match_when_theme_absent():
    finding = _finding(themes=[])
    matches = match_rules([finding], ENTITY, _policy(_rule(match=RuleMatchCriteria(themes=["sanctions"]))))
    assert matches == []

    combined = combine_rule_matches(matches)
    assert combined.overall_risk_rating == RiskRating.LOW
    assert combined.edd_level == "standard"
    assert combined.edd_required_steps == []


def test_single_rule_matches():
    finding = _finding(themes=["sanctions"])
    matches = match_rules([finding], ENTITY, _policy(_rule(match=RuleMatchCriteria(themes=["sanctions"]))))
    assert len(matches) == 1
    assert matches[0].triggering_finding_references == ["module2:ctos:r1:h1"]


def test_overlapping_matches_combine_to_the_higher_rating():
    """Two rules matching the same finding — a broad medium-rating rule and
    a stricter high-rating rule — must combine to the HIGHER rating, not
    average or first-match-wins."""
    finding = _finding(themes=["sanctions"], confidence_score=80, disposition_recommendation="high_priority_review")
    broad_rule = _rule(
        rule_id="BROAD",
        match=RuleMatchCriteria(themes=["sanctions"]),
        rating_contribution=RiskRating.MEDIUM,
        edd=EDDRequirement(level=EDDLevel.ENHANCED, required_steps=["broad step"]),
    )
    strict_rule = _rule(
        rule_id="STRICT",
        match=RuleMatchCriteria(themes=["sanctions"], min_disposition="high_priority_review", min_confidence_score=70),
        rating_contribution=RiskRating.HIGH,
        edd=EDDRequirement(level=EDDLevel.SENIOR_ESCALATION, required_steps=["strict step"]),
    )

    matches = match_rules([finding], ENTITY, _policy(broad_rule, strict_rule))
    assert {m.rule.rule_id for m in matches} == {"BROAD", "STRICT"}

    combined = combine_rule_matches(matches)
    assert combined.overall_risk_rating == RiskRating.HIGH
    assert combined.edd_level == "senior_escalation"
    assert set(combined.edd_required_steps) == {"broad step", "strict step"}  # union across ALL matched rules


def test_multiple_findings_can_trigger_the_same_rule_together():
    a = _finding(themes=["fraud"], finding_reference="module2:ctos:r1:h1")
    b = _finding(themes=["fraud"], finding_reference="module2:public_records:r2:h2")
    matches = match_rules([a, b], ENTITY, _policy(_rule(match=RuleMatchCriteria(themes=["fraud"]))))
    assert len(matches) == 1
    assert set(matches[0].triggering_finding_references) == {"module2:ctos:r1:h1", "module2:public_records:r2:h2"}


# --- False-positive exclusion --------------------------------------------


def test_likely_false_positive_is_excluded_from_rule_triggers_but_stays_visible():
    genuine = _finding(themes=["sanctions"], finding_reference="module2:ctos:r1:h1", disposition_recommendation="needs_review")
    false_positive = _finding(
        themes=["sanctions"], finding_reference="module2:ctos:r2:h2", disposition_recommendation="likely_false_positive"
    )

    survivors, excluded = split_excluded_findings([genuine, false_positive])
    assert [f.triage.finding_reference for f in survivors] == ["module2:ctos:r1:h1"]
    assert excluded == ["module2:ctos:r2:h2"]

    matches = match_rules(survivors, ENTITY, _policy(_rule(match=RuleMatchCriteria(themes=["sanctions"]))))
    assert matches[0].triggering_finding_references == ["module2:ctos:r1:h1"]  # the false positive never triggers


def test_all_findings_false_positive_yields_no_matches_but_all_stay_visible():
    fp = _finding(themes=["sanctions"], disposition_recommendation="likely_false_positive")
    survivors, excluded = split_excluded_findings([fp])
    assert survivors == []
    assert excluded == ["module2:ctos:r1:h1"]


# --- Match criteria: severity / confidence / disposition / entity attrs -


def test_min_severity_gate():
    rule = _rule(match=RuleMatchCriteria(themes=["sanctions"], min_severity="high"))
    low_sev = _finding(themes=["sanctions"], finding_summary=TriageFindingSummaryIn(source="ctos", headline="H", excerpt="E", severity="low"))
    high_sev = _finding(themes=["sanctions"], finding_summary=TriageFindingSummaryIn(source="ctos", headline="H", excerpt="E", severity="high"))

    assert match_rules([low_sev], ENTITY, _policy(rule)) == []
    assert len(match_rules([high_sev], ENTITY, _policy(rule))) == 1


def test_min_confidence_score_gate():
    rule = _rule(match=RuleMatchCriteria(themes=["sanctions"], min_confidence_score=70))
    low_conf = _finding(themes=["sanctions"], confidence_score=50)
    high_conf = _finding(themes=["sanctions"], confidence_score=80)

    assert match_rules([low_conf], ENTITY, _policy(rule)) == []
    assert len(match_rules([high_conf], ENTITY, _policy(rule))) == 1


def test_min_disposition_gate():
    rule = _rule(match=RuleMatchCriteria(themes=["sanctions"], min_disposition="high_priority_review"))
    needs_review = _finding(themes=["sanctions"], disposition_recommendation="needs_review")
    high_priority = _finding(themes=["sanctions"], disposition_recommendation="high_priority_review")

    assert match_rules([needs_review], ENTITY, _policy(rule)) == []
    assert len(match_rules([high_priority], ENTITY, _policy(rule))) == 1


def test_entity_type_gate():
    rule = _rule(match=RuleMatchCriteria(themes=["tax_offence"], entity_types=["vendor"]))
    finding = _finding(themes=["tax_offence"])

    vendor = EntityProfile(entity_id="vendor:1", entity_type=EntityType.VENDOR, legal_name="Vendor Co")
    director = EntityProfile(entity_id="director:1", entity_type=EntityType.DIRECTOR, legal_name="A Director")

    assert len(match_rules([finding], vendor, _policy(rule))) == 1
    assert match_rules([finding], director, _policy(rule)) == []


def test_nationality_gate():
    rule = _rule(match=RuleMatchCriteria(themes=["sanctions"], nationalities=["Malaysia"]))
    finding = _finding(themes=["sanctions"])

    malaysian = EntityProfile(entity_id="vendor:1", entity_type=EntityType.VENDOR, legal_name="X", nationality="Malaysia")
    singaporean = EntityProfile(entity_id="vendor:2", entity_type=EntityType.VENDOR, legal_name="Y", nationality="Singapore")

    assert len(match_rules([finding], malaysian, _policy(rule))) == 1
    assert match_rules([finding], singaporean, _policy(rule)) == []
