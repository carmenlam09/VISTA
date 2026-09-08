"""Historical outcome signal — Module 2's `prior_kyv` source (the spec's
prompt calls it `previous_kyv_reviews`; module2/backend/app/schemas/
screening.py names the real SourceName value `prior_kyv`) as a whole-entity
signal, surfaced alongside fresh analysis rather than silently applied.

Module 2's mock prior_kyv outcomes are `approved_with_conditions` and
`escalated` (see module2/backend/app/connectors/prior_kyv.py) — neither is
literally "a prior reviewer marked this a false positive." Both represent a
reviewer engaging substantively with a real concern rather than dismissing
it as noise, so both map to `true_hit` here; `unknown` covers "no prior
review found" (no hits, or the source errored/timed out). The mapping
structurally supports `false_positive` for when a real prior-review system
records an explicit "cleared" disposition — Module 2's current mock just
never emits one. This is an entity-level signal (Module 2 doesn't record
per-finding review outcomes), so the same signal is attached to every
finding for a given entity, not derived per finding.
"""

from app.schemas.triage import HistoricalOutcomeSignal, HistoricalPriorOutcome
from app.schemas.upstream import ScreeningResultIn, SourceStatus

_OUTCOME_TO_PRIOR: dict[str, HistoricalPriorOutcome] = {
    "escalated": HistoricalPriorOutcome.TRUE_HIT,
    "approved_with_conditions": HistoricalPriorOutcome.TRUE_HIT,
    "cleared": HistoricalPriorOutcome.FALSE_POSITIVE,
    "false_positive": HistoricalPriorOutcome.FALSE_POSITIVE,
}


def derive_historical_outcome_signal(results: list[ScreeningResultIn]) -> HistoricalOutcomeSignal:
    prior_kyv_result = next((r for r in results if r.source.value == "prior_kyv"), None)

    if prior_kyv_result is None or prior_kyv_result.status != SourceStatus.OK or not prior_kyv_result.hits:
        return HistoricalOutcomeSignal(prior_review_found=False, prior_outcome=HistoricalPriorOutcome.UNKNOWN)

    hit = prior_kyv_result.hits[0]
    raw_outcome = str(hit.raw.get("outcome", "")).lower()
    prior_outcome = _OUTCOME_TO_PRIOR.get(raw_outcome, HistoricalPriorOutcome.UNKNOWN)

    return HistoricalOutcomeSignal(
        prior_review_found=True,
        prior_outcome=prior_outcome,
        prior_review_date=hit.hit_date,
        prior_review_note=hit.description,
    )
