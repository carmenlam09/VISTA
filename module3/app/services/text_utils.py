"""Small shared text-normalization helpers used by dedup and relevance
filtering. Deliberately simple (lowercase, strip punctuation, drop common
legal suffixes) — real fuzzy matching is not the point here; catching
obvious duplicates and obvious name mismatches is."""

import re

_LEGAL_SUFFIXES = [
    "sdn bhd",
    "pte ltd",
    "berhad",
    "holdings",
    "group",
    "limited",
    "ltd",
    "llc",
    "inc",
    "corp",
    "co",
]

_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "for", "into", "of", "to", "is", "was", "were", "has",
    "have", "had", "in", "on", "at", "by", "with", "from", "over", "its", "it", "as", "that",
    "this", "be", "been", "will", "after", "amid",
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = _PUNCTUATION_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def normalize_name(name: str) -> str:
    """Strips trailing legal/corporate-form words repeatedly (so "X Holdings
    Sdn Bhd" reduces to "x", not just "x holdings"), trying longer suffixes
    first each pass so a multi-word suffix like "sdn bhd" is removed as a
    unit rather than leaving a dangling "bhd"."""
    normalized = normalize_text(name)
    suffixes_longest_first = sorted(_LEGAL_SUFFIXES, key=len, reverse=True)
    changed = True
    while changed:
        changed = False
        for suffix in suffixes_longest_first:
            if normalized.endswith(f" {suffix}"):
                normalized = normalized[: -(len(suffix) + 1)].strip()
                changed = True
                break
    return normalized


def token_set(text: str) -> set[str]:
    return set(normalize_text(text).split())


def content_token_set(text: str, exclude: set[str] | None = None) -> set[str]:
    """Token set with stopwords and any caller-supplied tokens (typically the
    entity's own name tokens) removed — useful when comparing two texts that
    both legitimately contain the same entity name and common function
    words, where that overlap would otherwise swamp the real signal."""
    tokens = token_set(text) - STOPWORDS
    if exclude:
        tokens -= exclude
    return tokens


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
