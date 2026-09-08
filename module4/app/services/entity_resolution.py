"""Deterministic entity-resolution scoring — explicitly NOT LLM-driven, per
the spec ("do not rely on the LLM for the similarity scoring itself, only
for reasoning over the results"). Produces the four MatchQuality sub-scores:
name similarity, nationality match, ID match, and ownership/relationship
overlap.

Two adaptations from the spec's illustrative schema, both because of gaps in
what Module 2's actual ScreeningHit carries (documented in module4/README.md):

- Module 2 hits have no separate "subject nationality"/"subject ID" field
  distinct from the queried entity, so nationality_match and id_match are
  computed by scanning the hit's own text/metadata for a mention of the
  *queried* entity's known nationality/ID values — a text-mention proxy,
  not a structured field comparison.
- Module 2's EntityProfile.related_entities carries no ownership percentage,
  so ownership_overlap is a text-mention signal too: does the finding's text
  corroborate relevance by naming one of the entity's known related parties
  (director, shareholder, UBO)?
"""

from dataclasses import dataclass

from app.schemas.entity import EntityProfile
from app.services.text_utils import best_substring_char_similarity, normalize_name, normalize_text, token_set

NAME_MATCH_MENTION_THRESHOLD = 0.55  # below this, a related-entity "mention" isn't counted as corroboration


@dataclass(frozen=True)
class NameMatchResult:
    score: float
    matched_name: str | None


def score_name_similarity(entity: EntityProfile, text: str) -> NameMatchResult:
    """Blends token coverage (do the name's own words appear in the text?)
    with character-level similarity of the best-matching window in the text
    (catches transliteration/spelling variants token overlap would miss
    entirely, e.g. "Tan Wei Ming" vs. "Tan Wei Meng"). Tries the legal name
    and every alias, keeping whichever scores highest."""
    candidates = [entity.legal_name, *entity.aliases]
    best = NameMatchResult(score=0.0, matched_name=None)

    for name in candidates:
        name_tokens = token_set(normalize_name(name)) or token_set(name)
        if not name_tokens:
            continue
        text_tokens = token_set(text)
        token_coverage = len(name_tokens & text_tokens) / len(name_tokens)
        char_sim = best_substring_char_similarity(name, text)
        combined = 0.5 * token_coverage + 0.5 * char_sim

        if combined > best.score:
            best = NameMatchResult(score=round(combined, 3), matched_name=name)

    return best


def score_nationality_match(entity: EntityProfile, text: str) -> bool:
    if not entity.nationality:
        return False
    return normalize_text(entity.nationality) in normalize_text(text)


def score_id_match(entity: EntityProfile, text: str, raw: dict | None = None) -> bool:
    haystack = normalize_text(text)
    raw_values = " ".join(str(v) for v in (raw or {}).values())
    haystack_with_raw = normalize_text(f"{text} {raw_values}")

    for id_number in entity.id_numbers:
        normalized_value = _normalize_id(id_number.value)
        if not normalized_value:
            continue
        if normalized_value in _normalize_id(haystack) or normalized_value in _normalize_id(haystack_with_raw):
            return True
    return False


def _normalize_id(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


@dataclass(frozen=True)
class OwnershipOverlapResult:
    score: float
    matched_related_entities: list[str]


def score_ownership_overlap(related_names: dict[str, str], text: str) -> OwnershipOverlapResult:
    """`related_names` maps related entity_id -> legal_name (from
    EntityLookupService.resolve_related_names). Returns the strongest single
    corroborating mention found, plus every related-entity name that cleared
    the mention threshold — a single strong hit (e.g. a named director) is
    real corroboration even if no other related party is mentioned."""
    if not related_names:
        return OwnershipOverlapResult(score=0.0, matched_related_entities=[])

    best_score = 0.0
    matched: list[str] = []
    for name in related_names.values():
        score = best_substring_char_similarity(name, text)
        name_tokens = token_set(normalize_name(name)) or token_set(name)
        token_coverage = len(name_tokens & token_set(text)) / len(name_tokens) if name_tokens else 0.0
        combined = max(score, token_coverage)
        if combined >= NAME_MATCH_MENTION_THRESHOLD:
            matched.append(name)
        best_score = max(best_score, combined)

    return OwnershipOverlapResult(score=round(best_score if matched else 0.0, 3), matched_related_entities=matched)
