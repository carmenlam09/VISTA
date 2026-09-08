"""Semantic similarity for retrieval (capability 3) — deliberately a local,
deterministic embedding rather than a call to an external provider.

Reasoning (see also module7/README.md "Storage & retrieval approach"):
Anthropic has no embeddings endpoint, and every prior module in this repo
treats Anthropic as the one optional AI provider with a local fallback —
introducing a second provider (e.g. OpenAI) just for this module would be a
bigger architectural decision than this task calls for. Feature hashing (the
"hashing trick": token/bigram term frequencies hashed into a fixed-size
vector, L2-normalized) is a real, well-established lightweight embedding
technique, not a toy — it needs no external API, no key, no model download,
and is fully deterministic and testable. `EmbeddingProvider` is an ABC
specifically so a real embedding API can be substituted later (a new
implementation of this interface) without touching retrieval_service.py.
"""

import hashlib
import math
import re
from abc import ABC, abstractmethod

from app.core.config import settings

_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "for", "into", "of", "to", "is", "was", "were", "has",
    "have", "had", "in", "on", "at", "by", "with", "from", "over", "its", "it", "as", "that",
    "this", "be", "been", "will", "after", "amid", "not", "no", "did", "does", "do",
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = _PUNCTUATION_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    return [t for t in normalize_text(text).split() if len(t) > 1 and t not in STOPWORDS]


def _stable_hash(token: str) -> int:
    """A hash stable across processes/runs — Python's built-in hash() is
    salted per-process for strings, which would make embeddings
    non-reproducible between the ingesting process and a later query."""
    return int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class LocalHashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic, dependency-free embedding via the hashing trick."""

    provider_name = "local-hashing"

    def __init__(self, dimensions: int | None = None) -> None:
        self.dimensions = dimensions if dimensions is not None else settings.embedding_dimensions

    def embed(self, text: str) -> list[float]:
        tokens = tokenize(text)
        vector = [0.0] * self.dimensions

        for token in tokens:
            vector[_stable_hash(token) % self.dimensions] += 1.0
        for first, second in zip(tokens, tokens[1:]):
            vector[_stable_hash(f"{first} {second}") % self.dimensions] += 0.5

        return _l2_normalize(vector)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Both vectors from `LocalHashingEmbeddingProvider` are already
    L2-normalized, so their dot product IS the cosine similarity — but this
    doesn't assume that, so it stays correct for any future provider too."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


embedding_provider: EmbeddingProvider = LocalHashingEmbeddingProvider()
