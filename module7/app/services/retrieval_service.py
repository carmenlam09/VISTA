"""Structured filtering + semantic similarity ranking (capability 3/4).
Retention-aware: a record older than its record_type's retain_days is
excluded from default results (`is_archived=True`) but never disappears —
`include_archived=true` surfaces it, and `include_superseded=true` surfaces
prior versions too. This is reference context for a reviewer, never a
decision — every response carries `disclaimer` (see schemas/retrieval.py).
"""

from datetime import datetime, time, timezone

from sqlalchemy.orm import Session

from app.core.time import ensure_utc
from app.models.record import KnowledgeRecordORM
from app.policy.loader import load_retention_policy
from app.schemas.record import RecordStatus, RecordType
from app.schemas.retention import RetentionPolicyConfig
from app.schemas.retrieval import RetrievalQuery, RetrievalResponse, RetrievalResult
from app.services.embedding import EmbeddingProvider, cosine_similarity, embedding_provider
from app.services.ingestion_service import _to_schema

MIN_SEMANTIC_SIMILARITY = 0.05  # filters out pure noise when a freeform query is given
ENTITY_MATCH_BONUS = 0.15
TAG_MATCH_BONUS = 0.1


class RetrievalService:
    def __init__(
        self,
        embedder: EmbeddingProvider | None = None,
        policy: RetentionPolicyConfig | None = None,
    ) -> None:
        self._embedder = embedder or embedding_provider
        self._policy = policy or load_retention_policy()

    def search(self, db: Session, query: RetrievalQuery) -> RetrievalResponse:
        rows = self._filtered_rows(db, query)
        query_embedding = self._embedder.embed(query.query_text) if query.query_text else None

        scored: list[tuple[float, str, KnowledgeRecordORM, bool]] = []
        for row in rows:
            is_archived = self._is_archived(row)
            if is_archived and not query.include_archived:
                continue

            score, reasons = self._score(row, query, query_embedding)
            if query_embedding is not None and not reasons:
                continue  # freeform query given but nothing — semantic or structured — matched at all

            scored.append((score, "; ".join(reasons) if reasons else "structured filter match", row, is_archived))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[: query.limit]

        results = [
            RetrievalResult(record=_to_schema(row), relevance_score=round(score, 4), match_reason=reason, is_archived=is_archived)
            for score, reason, row, is_archived in top
        ]
        return RetrievalResponse(results=results, query_echo=query, generated_at=datetime.now(timezone.utc))

    def _filtered_rows(self, db: Session, query: RetrievalQuery) -> list[KnowledgeRecordORM]:
        q = db.query(KnowledgeRecordORM)
        if query.entity_id:
            q = q.filter(KnowledgeRecordORM.entity_id == query.entity_id)
        if query.record_type:
            q = q.filter(KnowledgeRecordORM.record_type == query.record_type.value)
        if query.date_from:
            q = q.filter(KnowledgeRecordORM.timestamp >= datetime.combine(query.date_from, time.min, tzinfo=timezone.utc))
        if query.date_to:
            q = q.filter(KnowledgeRecordORM.timestamp <= datetime.combine(query.date_to, time.max, tzinfo=timezone.utc))
        if not query.include_superseded:
            q = q.filter(KnowledgeRecordORM.status == RecordStatus.ACTIVE.value)

        rows = q.all()
        if query.tags:
            rows = [r for r in rows if set(r.tags) & set(query.tags)]
        return rows

    def _is_archived(self, row: KnowledgeRecordORM) -> bool:
        retain_days = self._policy.retain_days_for(RecordType(row.record_type))
        age_days = (datetime.now(timezone.utc) - ensure_utc(row.timestamp)).days
        return age_days > retain_days

    def _score(
        self, row: KnowledgeRecordORM, query: RetrievalQuery, query_embedding: list[float] | None
    ) -> tuple[float, list[str]]:
        if query_embedding is None:
            # No freeform query: every row here already survived the structured SQL/tag
            # filtering in _filtered_rows, so it's an exact match on whatever was asked for —
            # fully relevant by definition, not a partial score.
            applied: list[str] = []
            if query.entity_id:
                applied.append("entity match")
            if query.record_type:
                applied.append(f"record_type match ({query.record_type.value})")
            if query.tags:
                matched_tags = sorted(set(row.tags) & set(query.tags))
                applied.append(f"tag match: {', '.join(matched_tags)}")
            if query.date_from or query.date_to:
                applied.append("date range match")
            return 1.0, applied or ["structured filter match"]

        # A freeform query: semantic similarity is the primary signal, with small bonuses as
        # tie-breakers for rows that also happen to match a structured filter.
        score = 0.0
        reasons: list[str] = []

        similarity = cosine_similarity(row.embedding, query_embedding)
        if similarity >= MIN_SEMANTIC_SIMILARITY:
            score += similarity
            reasons.append(f"semantic similarity {similarity:.2f}")

        if query.entity_id and row.entity_id == query.entity_id:
            score += ENTITY_MATCH_BONUS
            reasons.append("entity match")

        if query.tags:
            matched_tags = sorted(set(row.tags) & set(query.tags))
            if matched_tags:
                score += TAG_MATCH_BONUS * len(matched_tags)
                reasons.append(f"tag match: {', '.join(matched_tags)}")

        return min(score, 1.0), reasons


retrieval_service = RetrievalService()
