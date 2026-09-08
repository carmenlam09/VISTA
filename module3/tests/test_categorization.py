from app.schemas.adverse_news import AdverseNewsHitIn
from app.schemas.taxonomy import RiskTheme
from app.services.categorization_service import DeterministicCategorizer
from app.services.relevance_filter import KeywordMatch

categorizer = DeterministicCategorizer()


def _hit() -> AdverseNewsHitIn:
    return AdverseNewsHitIn(
        hit_id="hit-x",
        headline="Example Corp Investigated for Money Laundering",
        excerpt="Regulators opened a money laundering investigation into Example Corp.",
        publish_date="2025-03-10",
        publication="Wire",
        url="https://example.com/x",
        source_confidence="high",
    )


async def test_produces_a_finding_with_correct_source_attribution():
    hit = _hit()
    matches = [KeywordMatch(phrase="money laundering", themes=[RiskTheme.FINANCIAL_CRIME], negated=False, negation_phrase=None)]

    findings = await categorizer.categorize_hit("vendor:1", "Example Corp", hit, "result-123", matches)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.entity_id == "vendor:1"
    assert finding.themes == [RiskTheme.FINANCIAL_CRIME]
    assert finding.generator == "deterministic-fallback"
    assert finding.source_hit.result_id == "result-123"
    assert finding.source_hit.hit_id == "hit-x"
    assert finding.source_hit.headline == hit.headline
    assert finding.source_hit.url == hit.url
    assert "money laundering" in finding.rationale.lower()


async def test_negated_match_produces_no_finding():
    hit = _hit()
    matches = [
        KeywordMatch(
            phrase="money laundering", themes=[RiskTheme.FINANCIAL_CRIME], negated=True, negation_phrase="victim of"
        )
    ]

    findings = await categorizer.categorize_hit("vendor:1", "Example Corp", hit, "result-123", matches)

    assert findings == []


async def test_high_risk_theme_gets_high_severity():
    hit = _hit()
    matches = [KeywordMatch(phrase="OFAC", themes=[RiskTheme.SANCTIONS], negated=False, negation_phrase=None)]

    findings = await categorizer.categorize_hit("vendor:1", "Example Corp", hit, "result-123", matches)

    assert findings[0].severity.value == "high"


async def test_lower_risk_theme_gets_medium_severity():
    hit = _hit()
    matches = [KeywordMatch(phrase="data breach", themes=[RiskTheme.OPERATIONAL], negated=False, negation_phrase=None)]

    findings = await categorizer.categorize_hit("vendor:1", "Example Corp", hit, "result-123", matches)

    assert findings[0].severity.value == "medium"


async def test_multiple_candidate_matches_produce_multiple_findings_each_attributed_to_the_same_hit():
    hit = _hit()
    matches = [
        KeywordMatch(phrase="money laundering", themes=[RiskTheme.FINANCIAL_CRIME], negated=False, negation_phrase=None),
        KeywordMatch(phrase="fraud investigation", themes=[RiskTheme.FRAUD], negated=False, negation_phrase=None),
    ]

    findings = await categorizer.categorize_hit("vendor:1", "Example Corp", hit, "result-123", matches)

    assert len(findings) == 2
    assert all(f.source_hit.hit_id == "hit-x" for f in findings)
