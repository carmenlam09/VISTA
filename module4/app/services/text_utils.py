"""Shared text/name-normalization and similarity helpers for entity
resolution. Module 4's own copy of the normalization approach Module 3 uses
(module3/app/services/text_utils.py), plus a character-level similarity
measure Module 3 didn't need — transliteration variants ("Tan Wei Ming" vs.
"Tan Wei Meng") share almost no tokens but are nearly identical character-
for-character, which token-set overlap alone can't see.
"""

import re
from difflib import SequenceMatcher

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
    """Strips trailing legal/corporate-form words repeatedly, longest suffix
    first each pass, so "X Holdings Sdn Bhd" reduces to "x", not "x holdings"."""
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
    tokens = token_set(text) - STOPWORDS
    if exclude:
        tokens -= exclude
    return tokens


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def char_similarity(a: str, b: str) -> float:
    """Character-level similarity (0-1) via difflib's Ratcliff/Obershelp
    ratio — a dependency-free stand-in for edit-distance similarity, good at
    catching small spelling/transliteration variants between two short
    strings (e.g. name spellings)."""
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def best_substring_char_similarity(name: str, haystack: str, per_word_anchor_threshold: float = 0.8) -> float:
    """Finds the best character-level similarity between `name` and a
    name-length window of `haystack`, anchored at a word in `haystack` that
    closely matches one of `name`'s own words.

    The anchor step matters: without it, sliding a short window across long
    free text finds coincidental character overlap between totally
    unrelated phrases (a 3-word name like "Tan Wei Ming" can score >0.5
    against a random 3-word window just from shared letters and spaces).
    Requiring a real word-level anchor first — exact match, or close enough
    to catch a transliteration variant like "Meng" vs. "Ming" — means a
    score is only ever produced where there's already some genuine textual
    evidence, and the character-level score then refines *how good* that
    evidence is rather than inventing it from nothing.
    """
    name_norm = normalize_text(name)
    haystack_norm = normalize_text(haystack)
    if not name_norm or not haystack_norm:
        return 0.0
    if name_norm in haystack_norm:
        return 1.0

    name_words = name_norm.split()
    haystack_words = haystack_norm.split()
    width = len(name_words)

    def _word_anchors(haystack_word: str, name_word: str) -> bool:
        if haystack_word == name_word:
            return True
        # Fuzzy per-word matching only for words long enough that a high
        # ratio means something — short words (e.g. "an" vs "tan") can hit
        # ratio >= 0.8 from sharing a couple of letters purely by chance.
        if len(haystack_word) < 4 or len(name_word) < 4:
            return False
        return SequenceMatcher(None, haystack_word, name_word).ratio() >= per_word_anchor_threshold

    anchor_positions = {
        i for i, hw in enumerate(haystack_words) if any(_word_anchors(hw, nw) for nw in name_words)
    }
    if not anchor_positions:
        return 0.0

    best = 0.0
    for pos in anchor_positions:
        window_start = max(0, pos - width + 1)
        window_end = min(len(haystack_words), pos + width)
        for start in range(window_start, max(window_start + 1, window_end - width + 1)):
            candidate = " ".join(haystack_words[start : start + width])
            if not candidate:
                continue
            best = max(best, SequenceMatcher(None, name_norm, candidate).ratio())
    return best
