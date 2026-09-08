from app.schemas.entity import EntityProfile, EntityType
from app.services.entity_resolution import (
    score_id_match,
    score_name_similarity,
    score_nationality_match,
    score_ownership_overlap,
)


def _entity(**overrides) -> EntityProfile:
    defaults = dict(
        entity_id="director:x",
        entity_type=EntityType.DIRECTOR,
        legal_name="Tan Wei Ming",
        aliases=[],
        id_numbers=[],
        nationality="Malaysia",
    )
    defaults.update(overrides)
    return EntityProfile(**defaults)


# --- Name similarity: exact, common-name, and transliteration cases -----


def test_exact_name_mention_scores_near_one():
    entity = _entity()
    text = "Court registry shows an active civil suit naming Tan Wei Ming as a party."
    result = score_name_similarity(entity, text)
    assert result.score >= 0.95
    assert result.matched_name == "Tan Wei Ming"


def test_transliteration_variant_still_scores_high():
    """'Tan Wei Meng' shares no exact tokens with 'Tan Wei Ming' on the last
    word, but is a one-character spelling variant — character-level
    similarity should still catch it as a strong match."""
    entity = _entity()
    text = "Tan Wei Meng matches an entry on the OFAC Specially Designated Nationals list."
    result = score_name_similarity(entity, text)
    assert result.score >= 0.7


def test_unrelated_text_scores_low():
    """A completely different company/person should not score anywhere
    near a genuine match, even with fuzzy matching in play."""
    entity = _entity(legal_name="Meridian Capital Holdings Sdn Bhd", entity_type=EntityType.VENDOR)
    text = "A local bakery downtown won a regional pastry award this week."
    result = score_name_similarity(entity, text)
    assert result.score < 0.3


def test_short_word_coincidence_does_not_inflate_score():
    """Regression: short words like 'an' can hit a high character-similarity
    ratio against short name tokens (e.g. 'tan') purely by chance — that
    must not be treated as a name mention."""
    entity = _entity(legal_name="Meridian Capital Holdings Sdn Bhd", entity_type=EntityType.VENDOR)
    text = "CTOS records an active winding-up petition against Meridian Capital Holdings Sdn Bhd."
    unrelated = _entity()  # "Tan Wei Ming" — not mentioned in this text at all
    result = score_name_similarity(unrelated, text)
    assert result.score < 0.3


# --- Shared surname / common name across unrelated entities -------------


def test_shared_name_different_person_has_no_nationality_corroboration():
    """Same exact name, but the hit describes someone with a different
    nationality — a classic false-positive-shaped case. Name similarity
    should still be high (the text genuinely contains the name), but
    nationality_match must correctly come back False so the reasoning layer
    can weigh the contradiction instead of the name match alone deciding it."""
    entity = _entity(nationality="Malaysia")
    text = "Court registry shows an active civil suit naming Tan Wei Ming as a party. Nationality: Indonesia."
    name_result = score_name_similarity(entity, text)
    assert name_result.score >= 0.95
    assert score_nationality_match(entity, text) is False


def test_matching_nationality_is_detected():
    entity = _entity(nationality="Malaysia")
    text = "Tan Wei Meng matches a watchlist entry. Nationality on record: Malaysia."
    assert score_nationality_match(entity, text) is True


# --- ID matching ----------------------------------------------------------


def test_id_number_mentioned_in_text_matches():
    from app.schemas.entity import IdNumber

    entity = _entity(id_numbers=[IdNumber(type="NRIC", value="780512-08-5566")])
    text = "Records show NRIC 780512-08-5566 associated with the flagged individual."
    assert score_id_match(entity, text) is True


def test_id_number_mentioned_in_raw_metadata_matches():
    from app.schemas.entity import IdNumber

    entity = _entity(id_numbers=[IdNumber(type="SSM_NO", value="199001012345")])
    assert score_id_match(entity, "Some generic description.", raw={"company_reg_no": "199001012345"}) is True


def test_no_id_number_present_does_not_match():
    from app.schemas.entity import IdNumber

    entity = _entity(id_numbers=[IdNumber(type="NRIC", value="780512-08-5566")])
    assert score_id_match(entity, "No identifying numbers mentioned here at all.") is False


# --- Ownership / relationship overlap (partial ownership chains) --------


def test_related_entity_mention_corroborates_weak_direct_match():
    """The entity's own name is absent, but a related party (director) is
    named — that should register as a strong ownership/relationship
    overlap signal even though direct name similarity is near zero."""
    entity = _entity(legal_name="Meridian Capital Holdings Sdn Bhd", entity_type=EntityType.VENDOR)
    related_names = {"director:fixture-1": "Tan Wei Ming"}
    text = "A company linked to director Tan Wei Ming is facing scrutiny over governance concerns."

    name_result = score_name_similarity(entity, text)
    ownership = score_ownership_overlap(related_names, text)

    assert name_result.score < 0.3
    assert ownership.score >= 0.7
    assert "Tan Wei Ming" in ownership.matched_related_entities


def test_no_related_entity_mentioned_scores_zero_overlap():
    related_names = {"director:fixture-1": "Tan Wei Ming", "shareholder:fixture-1": "Harborview Investments Pte Ltd"}
    text = "CTOS records an active winding-up petition against Meridian Capital Holdings Sdn Bhd."
    ownership = score_ownership_overlap(related_names, text)
    assert ownership.score == 0.0
    assert ownership.matched_related_entities == []


def test_empty_related_entities_scores_zero_overlap():
    ownership = score_ownership_overlap({}, "Any text at all.")
    assert ownership.score == 0.0
    assert ownership.matched_related_entities == []
