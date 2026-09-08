from app.schemas.adverse_news import AdverseNewsHitIn
from app.services.dedup_service import collapse_duplicates
from app.services.relevance_filter import find_keyword_matches, is_relevant_to_entity
from app.taxonomy.loader import load_taxonomy

TAXONOMY = load_taxonomy()


def _hit(**overrides) -> AdverseNewsHitIn:
    defaults = dict(
        hit_id="h1",
        headline="Example Corp Faces Fraud Investigation",
        excerpt="Example Corp is under a fraud investigation.",
        publish_date="2025-01-01",
        publication="Wire",
        url="https://example.com/x",
        source_confidence="high",
    )
    defaults.update(overrides)
    return AdverseNewsHitIn(**defaults)


# --- Deduplication -----------------------------------------------------


def test_reworded_headlines_about_the_same_event_collapse():
    a = _hit(hit_id="a", headline="Meridian Capital Investigated for Money Laundering", publish_date="2025-03-10")
    b = _hit(hit_id="b", headline="Money Laundering Probe Opened Into Meridian Capital", publish_date="2025-03-10")
    deduped, dup_count = collapse_duplicates([a, b], legal_name="Meridian Capital Holdings Sdn Bhd")
    assert len(deduped) == 1
    assert dup_count == 1


def test_different_stories_about_the_same_entity_do_not_collapse():
    """Two genuinely different stories sharing the entity's name should not
    be treated as duplicates just because the name overlaps."""
    a = _hit(hit_id="a", headline="Meridian Capital Investigated for Money Laundering", publish_date="2025-03-10")
    b = _hit(hit_id="b", headline="Meridian Capital Fined for Regulatory Breach", publish_date="2025-04-01")
    deduped, dup_count = collapse_duplicates([a, b], legal_name="Meridian Capital Holdings Sdn Bhd")
    assert len(deduped) == 2
    assert dup_count == 0


def test_similar_headline_on_a_different_date_is_not_collapsed():
    a = _hit(hit_id="a", headline="Meridian Capital Investigated for Money Laundering", publish_date="2025-03-10")
    b = _hit(hit_id="b", headline="Meridian Capital Investigated for Money Laundering", publish_date="2025-09-01")
    deduped, dup_count = collapse_duplicates([a, b], legal_name="Meridian Capital Holdings Sdn Bhd")
    assert len(deduped) == 2
    assert dup_count == 0


def test_dedup_prefers_a_representative_with_a_url():
    a = _hit(hit_id="a", headline="Meridian Capital Money Laundering Probe", publish_date="2025-03-10", url=None)
    b = _hit(
        hit_id="b",
        headline="Money Laundering Probe Into Meridian Capital",
        publish_date="2025-03-10",
        url="https://example.com/has-url",
    )
    deduped, _ = collapse_duplicates([a, b], legal_name="Meridian Capital")
    assert deduped[0].hit_id == "b"


# --- Relevance filtering (near-miss name matches) -----------------------


def test_exact_name_match_is_relevant():
    hit = _hit(
        headline="Meridian Capital Holdings Sdn Bhd Investigated for Fraud",
        excerpt="Meridian Capital Holdings Sdn Bhd is under investigation.",
    )
    assert is_relevant_to_entity(hit, "Meridian Capital Holdings Sdn Bhd", []) is True


def test_near_miss_similarly_named_company_is_not_relevant():
    hit = _hit(
        headline="Meridian Logistics Pte Ltd Faces Fraud Investigation",
        excerpt="Singapore-based Meridian Logistics Pte Ltd, unrelated to other Meridian-branded firms, is under a fraud investigation.",
    )
    assert is_relevant_to_entity(hit, "Meridian Capital Holdings Sdn Bhd", []) is False


def test_alias_match_is_relevant():
    hit = _hit(headline="Meridian Capital Under Scrutiny", excerpt="Meridian Capital, as it's commonly known, is under scrutiny.")
    assert is_relevant_to_entity(hit, "Meridian Capital Holdings Sdn Bhd", ["Meridian Capital"]) is True


def test_completely_unrelated_article_is_not_relevant():
    hit = _hit(headline="Local Bakery Wins Award", excerpt="A small bakery downtown won a regional award for pastries.")
    assert is_relevant_to_entity(hit, "Meridian Capital Holdings Sdn Bhd", []) is False


# --- Keyword matching + negation / victim-vs-perpetrator framing --------


def test_direct_risk_keyword_matches_and_is_not_negated():
    hit = _hit(
        headline="Example Corp Investigated for Money Laundering",
        excerpt="Regulators opened a money laundering investigation into Example Corp.",
    )
    matches = find_keyword_matches(hit, TAXONOMY)
    assert any(m.phrase == "money laundering" and not m.negated for m in matches)


def test_victim_framing_is_flagged_as_negated():
    hit = _hit(
        headline="Example Corp Falls Victim to Embezzlement Scheme",
        excerpt="The company was the victim of an embezzlement scheme carried out by a former employee.",
    )
    matches = find_keyword_matches(hit, TAXONOMY)
    embezzlement_matches = [m for m in matches if m.phrase == "embezzlement"]
    assert embezzlement_matches
    assert all(m.negated for m in embezzlement_matches)


def test_cleared_of_is_flagged_as_negated():
    hit = _hit(
        headline="Example Corp Cleared of Tax Evasion Allegations",
        excerpt="A tribunal found the company was cleared of tax evasion after a lengthy investigation.",
    )
    matches = find_keyword_matches(hit, TAXONOMY)
    tax_matches = [m for m in matches if m.phrase == "tax evasion"]
    assert tax_matches
    assert all(m.negated for m in tax_matches)


def test_plaintiff_not_defendant_framing_is_flagged_as_negated():
    hit = _hit(
        headline="Class Action Lawsuit Filed by Example Corp",
        excerpt="A class action lawsuit was filed by Example Corp against a former supplier.",
    )
    matches = find_keyword_matches(hit, TAXONOMY)
    lawsuit_matches = [m for m in matches if m.phrase == "class action lawsuit"]
    assert lawsuit_matches
    assert all(m.negated for m in lawsuit_matches)


def test_no_keyword_match_on_unrelated_text():
    hit = _hit(headline="Example Corp Opens New Office", excerpt="The company announced a new regional office.")
    matches = find_keyword_matches(hit, TAXONOMY)
    assert matches == []
