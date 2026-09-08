"""Orchestrates the full pipeline: fetch -> dedup -> relevance filter ->
keyword candidates -> AI categorization -> AdverseMediaScreeningResponse.

This is Module 4's expected entry point into Module 3's output — keep
`screen_entity` a clean, UI-independent function."""

from app.schemas.adverse_news import AdverseNewsBundle
from app.schemas.finding import AdverseMediaScreeningResponse
from app.schemas.taxonomy import TaxonomyConfig
from app.services.adverse_news_source import AdverseNewsSource, adverse_news_source
from app.services.categorization_service import AICategorizer, categorizer
from app.services.dedup_service import collapse_duplicates
from app.services.relevance_filter import find_keyword_matches, is_relevant_to_entity
from app.taxonomy.loader import load_taxonomy


class ScreeningEngine:
    def __init__(
        self,
        source: AdverseNewsSource | None = None,
        taxonomy: TaxonomyConfig | None = None,
        ai_categorizer: AICategorizer | None = None,
    ) -> None:
        self._source = source or adverse_news_source
        self._taxonomy = taxonomy or load_taxonomy()
        self._categorizer = ai_categorizer or categorizer

    async def screen_entity(self, entity_id: str) -> AdverseMediaScreeningResponse:
        bundle = self._source.get_bundle(entity_id)
        if bundle is None:
            return AdverseMediaScreeningResponse(
                entity_id=entity_id,
                findings=[],
                hits_considered=0,
                duplicates_collapsed=0,
                filtered_irrelevant=0,
                suppressed_by_negation=0,
            )
        return await self._screen_bundle(bundle)

    async def _screen_bundle(self, bundle: AdverseNewsBundle) -> AdverseMediaScreeningResponse:
        deduped, duplicates_collapsed = collapse_duplicates(bundle.hits, legal_name=bundle.legal_name)

        relevant_hits = []
        filtered_irrelevant = 0
        for hit in deduped:
            if is_relevant_to_entity(hit, bundle.legal_name, bundle.aliases):
                relevant_hits.append(hit)
            else:
                filtered_irrelevant += 1

        findings = []
        suppressed_by_negation = 0
        for hit in relevant_hits:
            matches = find_keyword_matches(hit, self._taxonomy)
            suppressed_by_negation += sum(1 for m in matches if m.negated)
            hit_findings = await self._categorizer.categorize_hit(
                bundle.entity_id, bundle.legal_name, hit, bundle.result_id, matches
            )
            findings.extend(hit_findings)

        return AdverseMediaScreeningResponse(
            entity_id=bundle.entity_id,
            findings=findings,
            hits_considered=len(bundle.hits),
            duplicates_collapsed=duplicates_collapsed,
            filtered_irrelevant=filtered_irrelevant,
            suppressed_by_negation=suppressed_by_negation,
        )


screening_engine = ScreeningEngine()
