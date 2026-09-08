"""Two jobs that run before AI categorization, to cut cost and noise:

1. `is_relevant_to_entity` — is this hit actually about our entity, or a
   near-miss name collision (a different, similarly-named company)?
2. `find_keyword_matches` — candidate taxonomy matches for a hit, each
   flagged `negated` when a configured negation-guard phrase is also present
   (victim framing, exoneration, plaintiff-not-defendant). Negated matches
   are surfaced, not silently dropped — the caller decides what to do with
   them (screening_engine suppresses them from findings but still counts
   them, so the suppression is visible in the response).

Real contextual judgment (is "fraud" in this specific sentence about the
entity committing fraud or being a victim of it) is deliberately left to the
AI categorization step per the spec — negation_guard is a blunt, testable
heuristic the deterministic fallback can run without an LLM, not a
replacement for that judgment.
"""

from dataclasses import dataclass

from app.core.config import settings
from app.schemas.adverse_news import AdverseNewsHitIn
from app.schemas.taxonomy import RiskTheme, TaxonomyConfig
from app.services.text_utils import jaccard_similarity, normalize_name, normalize_text, token_set


@dataclass(frozen=True)
class KeywordMatch:
    phrase: str
    themes: list[RiskTheme]
    negated: bool
    negation_phrase: str | None


def is_relevant_to_entity(
    hit: AdverseNewsHitIn,
    legal_name: str,
    aliases: list[str] | None = None,
    token_overlap_threshold: float | None = None,
) -> bool:
    haystack = normalize_text(f"{hit.headline} {hit.excerpt}")

    for name in [legal_name, *(aliases or [])]:
        normalized_name = normalize_name(name)
        if normalized_name and normalized_name in haystack:
            return True

    threshold = token_overlap_threshold if token_overlap_threshold is not None else settings.relevance_token_overlap_threshold
    return jaccard_similarity(token_set(legal_name), token_set(f"{hit.headline} {hit.excerpt}")) >= threshold


def find_keyword_matches(hit: AdverseNewsHitIn, taxonomy: TaxonomyConfig) -> list[KeywordMatch]:
    haystack = normalize_text(f"{hit.headline} {hit.excerpt}")
    matches: list[KeywordMatch] = []

    for entry in taxonomy.keywords:
        phrase_norm = normalize_text(entry.phrase)
        if not phrase_norm or phrase_norm not in haystack:
            continue
        negation_phrase = next(
            (neg for neg in entry.negation_guard if normalize_text(neg) in haystack),
            None,
        )
        matches.append(
            KeywordMatch(
                phrase=entry.phrase,
                themes=entry.themes,
                negated=negation_phrase is not None,
                negation_phrase=negation_phrase,
            )
        )
    return matches
