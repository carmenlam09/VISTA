from app.schemas.triage import HistoricalPriorOutcome
from app.schemas.upstream import ScreeningHitIn, ScreeningResultIn
from app.services.historical_outcome import derive_historical_outcome_signal


def _prior_kyv_result(**overrides) -> ScreeningResultIn:
    defaults = dict(
        result_id="r1",
        entity_id="vendor:1",
        source="prior_kyv",
        status="ok",
        queried_at="2025-01-01T00:00:00Z",
        hit_count=1,
        hits=[],
    )
    defaults.update(overrides)
    return ScreeningResultIn(**defaults)


def test_escalated_outcome_maps_to_true_hit():
    result = _prior_kyv_result(
        hits=[
            ScreeningHitIn(
                hit_id="h1",
                title="Prior KYV review: escalated",
                description="Escalated to compliance.",
                hit_date="2024-09-15",
                confidence="high",
                raw={"outcome": "escalated"},
            )
        ]
    )
    signal = derive_historical_outcome_signal([result])
    assert signal.prior_review_found is True
    assert signal.prior_outcome == HistoricalPriorOutcome.TRUE_HIT
    assert str(signal.prior_review_date) == "2024-09-15"


def test_approved_with_conditions_maps_to_true_hit():
    result = _prior_kyv_result(
        hits=[
            ScreeningHitIn(
                hit_id="h1",
                title="Prior KYV review: approved with conditions",
                description="Approved with monitoring.",
                hit_date="2024-06-01",
                confidence="high",
                raw={"outcome": "approved_with_conditions"},
            )
        ]
    )
    signal = derive_historical_outcome_signal([result])
    assert signal.prior_outcome == HistoricalPriorOutcome.TRUE_HIT


def test_cleared_outcome_maps_to_false_positive():
    """Module 2's current mock never emits this outcome, but the mapping
    structurally supports a real prior-review system that does."""
    result = _prior_kyv_result(
        hits=[
            ScreeningHitIn(
                hit_id="h1",
                title="Prior KYV review: cleared",
                description="Cleared, no concerns.",
                hit_date="2024-06-01",
                confidence="high",
                raw={"outcome": "cleared"},
            )
        ]
    )
    signal = derive_historical_outcome_signal([result])
    assert signal.prior_outcome == HistoricalPriorOutcome.FALSE_POSITIVE


def test_no_prior_kyv_source_present_is_unknown():
    signal = derive_historical_outcome_signal([])
    assert signal.prior_review_found is False
    assert signal.prior_outcome == HistoricalPriorOutcome.UNKNOWN


def test_prior_kyv_present_but_no_hits_is_unknown():
    result = _prior_kyv_result(hit_count=0, hits=[])
    signal = derive_historical_outcome_signal([result])
    assert signal.prior_review_found is False
    assert signal.prior_outcome == HistoricalPriorOutcome.UNKNOWN


def test_prior_kyv_source_errored_is_unknown_not_a_false_signal():
    result = _prior_kyv_result(status="error", hit_count=0, hits=[])
    signal = derive_historical_outcome_signal([result])
    assert signal.prior_review_found is False
    assert signal.prior_outcome == HistoricalPriorOutcome.UNKNOWN
