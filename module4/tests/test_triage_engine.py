"""End-to-end: fixture entities + Module 2/3-shaped fixture data -> ranked
triage list, via the same TriageEngine the API route uses. Runs entirely on
the deterministic reasoning fallback."""

from app.schemas.triage import Disposition, FindingSource


async def test_high_risk_entity_produces_ranked_high_priority_findings(fixture_triage_engine):
    results = await fixture_triage_engine.run_triage("vendor:fixture-1")

    # Three triaged findings: ctos, public_records (both Module 2, exact name
    # match + escalated history), and adverse_news (Module 3, weak name match
    # but corroborated by a related-director mention). prior_kyv is excluded
    # — it's the historical-signal input, not a triaged finding itself.
    assert len(results) == 3
    sources = {r.finding_summary.source for r in results}
    assert sources == {"ctos", "public_records", "adverse_news"}

    # Ranked: high_priority_review items first, never hidden even when low.
    dispositions = [r.disposition_recommendation for r in results]
    assert dispositions[0] == Disposition.HIGH_PRIORITY_REVIEW
    assert all(
        _rank(dispositions[i]) <= _rank(dispositions[i + 1]) for i in range(len(dispositions) - 1)
    )

    adverse = next(r for r in results if r.finding_summary.source == "adverse_news")
    assert adverse.finding_source == FindingSource.MODULE3
    assert adverse.match_quality.ownership_overlap_score >= 0.7
    assert "Tan Wei Ming" in adverse.match_quality.matched_related_entities

    for r in results:
        assert r.historical_outcome_signal.prior_review_found is True
        assert r.label.startswith("AI-suggested")  # never presented as a resolved status


async def test_common_name_different_person_is_not_auto_dismissed_or_auto_confirmed(fixture_triage_engine):
    """director:fixture-1's public_records hit names the entity exactly but
    with a contradicting nationality — this must land in needs_review, not
    be silently waved through as high priority nor dismissed as noise."""
    results = await fixture_triage_engine.run_triage("director:fixture-1")

    public_records = next(r for r in results if r.finding_summary.source == "public_records")
    assert public_records.match_quality.name_similarity_score >= 0.95
    assert public_records.match_quality.nationality_match is False
    assert public_records.disposition_recommendation == Disposition.NEEDS_REVIEW


async def test_transliteration_variant_is_surfaced_for_review(fixture_triage_engine):
    results = await fixture_triage_engine.run_triage("director:fixture-1")

    netreveal = next(r for r in results if r.finding_summary.source == "netreveal")
    assert netreveal.match_quality.name_similarity_score >= 0.7
    assert netreveal.match_quality.nationality_match is True
    assert netreveal.disposition_recommendation != Disposition.LIKELY_FALSE_POSITIVE


async def test_clean_entity_has_no_findings(fixture_triage_engine):
    results = await fixture_triage_engine.run_triage("vendor:fixture-clean")
    assert results == []


async def test_approved_with_conditions_history_still_counts_as_a_true_hit_signal(fixture_triage_engine):
    results = await fixture_triage_engine.run_triage("vendor:fixture-conditions")
    assert len(results) == 1
    assert results[0].historical_outcome_signal.prior_outcome.value == "true_hit"
    assert results[0].disposition_recommendation == Disposition.HIGH_PRIORITY_REVIEW


async def test_unknown_entity_returns_empty_list(fixture_triage_engine):
    results = await fixture_triage_engine.run_triage("vendor:does-not-exist")
    assert results == []


async def test_every_result_has_a_traceable_finding_reference(fixture_triage_engine):
    results = await fixture_triage_engine.run_triage("vendor:fixture-1")
    for r in results:
        assert r.finding_reference
        prefix = "module2:" if r.finding_source == FindingSource.MODULE2 else "module3:"
        assert r.finding_reference.startswith(prefix)


def _rank(disposition: Disposition) -> int:
    return {Disposition.HIGH_PRIORITY_REVIEW: 0, Disposition.NEEDS_REVIEW: 1, Disposition.LIKELY_FALSE_POSITIVE: 2}[
        disposition
    ]
