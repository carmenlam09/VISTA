from pathlib import Path

import pytest

from app.services.adverse_news_source import AdverseNewsSource

NONEXISTENT_DB = Path("/nonexistent/for-tests.db")


@pytest.fixture()
def fixture_source() -> AdverseNewsSource:
    """An AdverseNewsSource that always falls back to the bundled fixtures,
    regardless of whatever is in Module 2's/Module 1's real databases on
    this machine — tests must be deterministic."""
    return AdverseNewsSource(module2_db_path=str(NONEXISTENT_DB), module1_db_path=str(NONEXISTENT_DB))
