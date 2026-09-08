"""Collapses duplicate/near-duplicate articles about the same event — common
in adverse news, where many outlets republish the same wire story under a
reworded headline (word order changed, a synonym swapped in). Similarity is
measured as content-token (bag-of-words, entity name and stopwords excluded)
overlap rather than a character-level diff, since reordering — "Money
Laundering Probe Opened Into X" vs. "X Investigated for Money Laundering" —
should still count as the same story.

The entity name is excluded deliberately: every hit about this entity
contains its name, so leaving those tokens in would make two *unrelated*
stories about the same company (e.g. a money-laundering probe and, months
later, an unrelated regulatory fine) look artificially similar — the shared
name tokens alone can outweigh the actual topic words.
"""

from app.core.config import settings
from app.schemas.adverse_news import AdverseNewsHitIn
from app.services.text_utils import content_token_set, jaccard_similarity, normalize_name


def _headline_similarity(a: str, b: str, name_tokens: set[str]) -> float:
    return jaccard_similarity(content_token_set(a, exclude=name_tokens), content_token_set(b, exclude=name_tokens))


def _is_near_duplicate(a: AdverseNewsHitIn, b: AdverseNewsHitIn, threshold: float, name_tokens: set[str]) -> bool:
    if a.publish_date and b.publish_date and a.publish_date != b.publish_date:
        return False  # different reporting dates: treat as distinct events even if headlines rhyme
    return _headline_similarity(a.headline, b.headline, name_tokens) >= threshold


def _pick_representative(group: list[AdverseNewsHitIn]) -> AdverseNewsHitIn:
    with_url = [h for h in group if h.url]
    return (with_url or group)[0]


def collapse_duplicates(
    hits: list[AdverseNewsHitIn],
    legal_name: str = "",
    threshold: float | None = None,
) -> tuple[list[AdverseNewsHitIn], int]:
    """Groups near-duplicate hits and keeps one representative per group.

    Returns (deduplicated_hits, duplicates_collapsed_count) where the count
    is how many hits were dropped (group size - 1, summed across groups).
    """
    sim_threshold = threshold if threshold is not None else settings.dedup_similarity_threshold
    name_tokens = set(normalize_name(legal_name).split()) if legal_name else set()
    groups: list[list[AdverseNewsHitIn]] = []

    for hit in hits:
        placed = False
        for group in groups:
            if _is_near_duplicate(group[0], hit, sim_threshold, name_tokens):
                group.append(hit)
                placed = True
                break
        if not placed:
            groups.append([hit])

    representatives = [_pick_representative(group) for group in groups]
    duplicates_collapsed = len(hits) - len(representatives)
    return representatives, duplicates_collapsed
