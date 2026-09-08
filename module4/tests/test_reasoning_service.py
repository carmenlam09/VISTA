from app.schemas.entity import EntityProfile, EntityType
from app.schemas.triage import Disposition, FindingSummary, HistoricalOutcomeSignal, HistoricalPriorOutcome, MatchQuality
from app.services.reasoning_service import DeterministicReasoningService

reasoner = DeterministicReasoningService()

ENTITY = EntityProfile(entity_id="vendor:1", entity_type=EntityType.VENDOR, legal_name="Example Corp")
NO_HISTORY = HistoricalOutcomeSignal(prior_review_found=False, prior_outcome=HistoricalPriorOutcome.UNKNOWN)


def _finding(**overrides) -> FindingSummary:
    defaults = dict(source="ctos", headline="Headline", excerpt="Excerpt.")
    defaults.update(overrides)
    return FindingSummary(**defaults)


async def test_strong_signals_reach_high_priority_review():
    match = MatchQuality(name_similarity_score=1.0, matched_name="Example Corp", nationality_match=True, id_match=True, ownership_overlap_score=0.0)
    result = await reasoner.score(ENTITY, _finding(), match, NO_HISTORY)
    assert result.disposition == Disposition.HIGH_PRIORITY_REVIEW
    assert result.confidence_score >= 60


async def test_weak_signals_are_likely_false_positive():
    match = MatchQuality(name_similarity_score=0.1, matched_name=None, nationality_match=False, id_match=False, ownership_overlap_score=0.0)
    result = await reasoner.score(ENTITY, _finding(), match, NO_HISTORY)
    assert result.disposition == Disposition.LIKELY_FALSE_POSITIVE
    assert result.confidence_score < 35


async def test_name_match_alone_with_no_corroboration_is_needs_review_not_high_priority():
    """Per the spec's hard requirement, a name match by itself must not be
    enough to reach high_priority_review — that's exactly the "common name"
    case a human needs to weigh, not one this module resolves on its own."""
    match = MatchQuality(name_similarity_score=1.0, matched_name="Example Corp", nationality_match=False, id_match=False, ownership_overlap_score=0.0)
    result = await reasoner.score(ENTITY, _finding(), match, NO_HISTORY)
    assert result.disposition == Disposition.NEEDS_REVIEW


async def test_escalated_prior_review_raises_confidence():
    history = HistoricalOutcomeSignal(
        prior_review_found=True, prior_outcome=HistoricalPriorOutcome.TRUE_HIT, prior_review_note="escalated"
    )
    weak_match = MatchQuality(name_similarity_score=0.3, matched_name=None, nationality_match=False, id_match=False, ownership_overlap_score=0.0)

    with_history = await reasoner.score(ENTITY, _finding(), weak_match, history)
    without_history = await reasoner.score(ENTITY, _finding(), weak_match, NO_HISTORY)

    assert with_history.confidence_score > without_history.confidence_score


async def test_prior_false_positive_lowers_confidence():
    history = HistoricalOutcomeSignal(
        prior_review_found=True, prior_outcome=HistoricalPriorOutcome.FALSE_POSITIVE, prior_review_note="cleared"
    )
    match = MatchQuality(name_similarity_score=1.0, matched_name="Example Corp", nationality_match=True, id_match=False, ownership_overlap_score=0.0)

    with_history = await reasoner.score(ENTITY, _finding(), match, history)
    without_history = await reasoner.score(ENTITY, _finding(), match, NO_HISTORY)

    assert with_history.confidence_score < without_history.confidence_score


async def test_confidence_score_is_bounded_0_to_100():
    match = MatchQuality(name_similarity_score=1.0, matched_name="Example Corp", nationality_match=True, id_match=True, ownership_overlap_score=1.0)
    history = HistoricalOutcomeSignal(
        prior_review_found=True, prior_outcome=HistoricalPriorOutcome.TRUE_HIT, prior_review_note="escalated"
    )
    result = await reasoner.score(ENTITY, _finding(severity="high"), match, history)
    assert 0 <= result.confidence_score <= 100


async def test_rationale_cites_every_signal():
    match = MatchQuality(name_similarity_score=0.79, matched_name="Example Corp", nationality_match=True, id_match=False, ownership_overlap_score=0.0)
    history = HistoricalOutcomeSignal(prior_review_found=False, prior_outcome=HistoricalPriorOutcome.UNKNOWN)

    result = await reasoner.score(ENTITY, _finding(), match, history)

    assert "name similarity" in result.rationale
    assert "nationality" in result.rationale
    assert "ID" in result.rationale
    assert "prior KYV review" in result.rationale
    assert str(result.confidence_score) in result.rationale


async def test_never_recommends_beyond_the_three_defined_dispositions():
    for name_score in (0.0, 0.3, 0.6, 1.0):
        match = MatchQuality(name_similarity_score=name_score, matched_name=None, nationality_match=False, id_match=False, ownership_overlap_score=0.0)
        result = await reasoner.score(ENTITY, _finding(), match, NO_HISTORY)
        assert result.disposition in {Disposition.LIKELY_FALSE_POSITIVE, Disposition.NEEDS_REVIEW, Disposition.HIGH_PRIORITY_REVIEW}
