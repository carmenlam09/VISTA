"""Retrieval-relevance tests against the bundled fixture history
(fixtures/sample_records.json) — confirms a query returns the expected
matches and excludes clearly irrelevant ones, per the spec's example:
"past reviews involving name-collision false positives for this director."
"""

from app.schemas.retrieval import RetrievalQuery


def test_freeform_query_surfaces_the_name_collision_record_first(seeded_db, retrieval):
    response = retrieval.search(
        seeded_db, RetrievalQuery(query_text="name collision false positive sanctions watchlist")
    )

    assert response.results  # something matched
    top = response.results[0]
    assert top.record.entity_id == "director:knowledge-1"
    assert top.record.record_type == "false_positive_decision"
    assert "name_collision" in top.record.tags

    # clearly irrelevant records (unrelated entities/topics) must not appear
    result_entities = {r.record.entity_id for r in response.results}
    assert "vendor:knowledge-3" not in result_entities  # routine clean KYV review, unrelated
    assert "vendor:knowledge-4" not in result_entities  # unrelated approval record


def test_freeform_query_scoped_to_an_entity_only_returns_that_entitys_records(seeded_db, retrieval):
    response = retrieval.search(
        seeded_db,
        RetrievalQuery(query_text="name collision false positive for this director", entity_id="director:knowledge-1"),
    )

    assert response.results
    assert all(r.record.entity_id == "director:knowledge-1" for r in response.results)
    assert response.results[0].record.record_type == "false_positive_decision"


def test_unrelated_freeform_query_does_not_surface_the_name_collision_record_at_the_top(seeded_db, retrieval):
    """A query about something else entirely (tax arrears) should rank the
    tax record above (or instead of) the sanctions name-collision record."""
    response = retrieval.search(seeded_db, RetrievalQuery(query_text="tax arrears dispute outstanding"))

    assert response.results
    assert response.results[0].record.entity_id == "vendor:knowledge-2"
    assert response.results[0].record.record_type == "false_positive_decision"


def test_structured_filter_by_record_type_returns_both_matching_entities(seeded_db, retrieval):
    response = retrieval.search(seeded_db, RetrievalQuery(record_type="false_positive_decision"))
    entities = {r.record.entity_id for r in response.results}
    assert entities == {"director:knowledge-1", "vendor:knowledge-2"}
    assert all(r.relevance_score == 1.0 for r in response.results)  # exact structured match


def test_tag_filter_narrows_to_matching_records(seeded_db, retrieval):
    response = retrieval.search(seeded_db, RetrievalQuery(tags=["name_collision"]))
    assert len(response.results) == 1
    assert response.results[0].record.entity_id == "director:knowledge-1"


def test_old_fixture_record_excluded_by_default_and_included_when_asked(seeded_db, retrieval):
    default_response = retrieval.search(seeded_db, RetrievalQuery(entity_id="vendor:knowledge-5"))
    assert default_response.results == []

    archived_response = retrieval.search(seeded_db, RetrievalQuery(entity_id="vendor:knowledge-5", include_archived=True))
    assert len(archived_response.results) == 1
    assert archived_response.results[0].is_archived is True


def test_response_always_carries_the_reviewer_context_disclaimer(seeded_db, retrieval):
    response = retrieval.search(seeded_db, RetrievalQuery(entity_id="director:knowledge-1"))
    assert "not a recommendation" in response.disclaimer.lower() or "reference" in response.disclaimer.lower()


def test_no_query_at_all_returns_everything_active_and_unarchived(seeded_db, retrieval):
    response = retrieval.search(seeded_db, RetrievalQuery(limit=100))
    # 7 fixture records minus the 1 that's past retention by default
    assert len(response.results) == 6
    assert all(not r.is_archived for r in response.results)
