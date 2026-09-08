"""Adapter over Module 3's output.

Module 3 has no database of its own — it's fully stateless, computing
adverse-media findings fresh on every API call (see module3/README.md). So
"live" means an HTTP call to Module 3's running server, not a file read. If
unreachable, falls back to fixtures/*/sample_adverse_media_findings.json for
that entity rather than failing the whole report.
"""

import json
from pathlib import Path

import httpx

from app.core.config import settings
from app.schemas.upstream import AdverseMediaFindingIn

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


def _load_fixture_findings(fixtures_subdir: str, entity_id: str) -> list[AdverseMediaFindingIn]:
    path = FIXTURES_DIR / fixtures_subdir / "sample_adverse_media_findings.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [AdverseMediaFindingIn.model_validate(row) for row in data if row["entity_id"] == entity_id]


class Module3Source:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        fixtures_subdir: str = "complete",
    ) -> None:
        self._base_url = base_url or settings.module3_base_url
        self._timeout = timeout_seconds if timeout_seconds is not None else settings.module3_timeout_seconds
        self._fixtures_subdir = fixtures_subdir

    async def get_findings_for_entity(self, entity_id: str) -> list[AdverseMediaFindingIn]:
        live = await self._fetch_live(entity_id)
        if live is not None:
            return live
        return _load_fixture_findings(self._fixtures_subdir, entity_id)

    async def _fetch_live(self, entity_id: str) -> list[AdverseMediaFindingIn] | None:
        url = f"{self._base_url}/api/entities/{entity_id}/adverse-media-findings"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException):
            return None
        body = response.json()
        return [AdverseMediaFindingIn.model_validate(f) for f in body.get("findings", [])]


module3_source = Module3Source()
