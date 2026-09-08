"""Recovers the risk theme(s) for a Module 4 finding, working around a real
gap: Module 4's FindingSummary carries no theme through from either Module
2's `risk_categories` or Module 3's `themes` (see module5/README.md).

For `module2:{source}:{result_id}:{hit_id}` references: looks up the exact
hit by (result_id, hit_id) in Module 2's screening.db — both ids are stable
there (Module 2 persists its data), so this is a precise, reliable lookup.

For `module3:{finding_id}` references: a second real gap. Module 3 is
stateless and regenerates a fresh `finding_id` (and `hit_id`) on every call
(see module3/app/services/categorization_service.py), so the finding_id
captured in Module 4's persisted triage record will almost never match a
live Module 3 call's output — Module 3's *content* is deterministic for the
same underlying data, but its generated ids are not. Matched by the
finding's headline instead, which Module 4's FindingSummary does persist
verbatim. Falls back to an empty theme list (not an error) if no match is
found, e.g. because the underlying adverse-news data changed since the
original triage run.

Both live paths fall back to this module's own fixtures when unavailable,
same as every other read-only adapter in this repo.
"""

import json
import sqlite3
from pathlib import Path

import httpx

from app.core.config import settings

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"
MODULE2_FIXTURES_PATH = FIXTURES_DIR / "sample_screening_results.json"
MODULE3_FIXTURES_PATH = FIXTURES_DIR / "sample_adverse_media_findings.json"


class ThemeEnrichmentService:
    def __init__(
        self,
        module2_db_path: str | None = None,
        module3_base_url: str | None = None,
        module3_timeout_seconds: float | None = None,
    ) -> None:
        self._module2_db_path = Path(module2_db_path or settings.module2_db_path)
        self._module3_base_url = module3_base_url or settings.module3_base_url
        self._module3_timeout = (
            module3_timeout_seconds if module3_timeout_seconds is not None else settings.module3_timeout_seconds
        )

    async def themes_for(self, entity_id: str, finding_reference: str, headline: str) -> list[str]:
        parts = finding_reference.split(":")
        if parts[0] == "module2" and len(parts) == 4:
            _, _source, result_id, hit_id = parts
            return self._module2_themes(result_id, hit_id)
        if parts[0] == "module3" and len(parts) == 2:
            return await self._module3_themes(entity_id, headline)
        return []

    # --- Module 2 (stable ids: direct lookup) ---

    def _module2_themes(self, result_id: str, hit_id: str) -> list[str]:
        themes = self._read_live_module2_hit(result_id, hit_id)
        if themes is not None:
            return themes
        return self._read_fixture_module2_hit(result_id, hit_id)

    def _read_live_module2_hit(self, result_id: str, hit_id: str) -> list[str] | None:
        if not self._module2_db_path.exists():
            return None
        conn = sqlite3.connect(f"file:{self._module2_db_path.as_posix()}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT hits FROM screening_results WHERE id = ?", (result_id,)).fetchone()
        except sqlite3.DatabaseError:
            return None
        finally:
            conn.close()
        if row is None:
            return None
        for hit in json.loads(row[0]):
            if hit.get("hit_id") == hit_id:
                return hit.get("risk_categories", [])
        return None

    def _read_fixture_module2_hit(self, result_id: str, hit_id: str) -> list[str]:
        data = json.loads(MODULE2_FIXTURES_PATH.read_text(encoding="utf-8"))
        for result in data:
            if result["result_id"] != result_id:
                continue
            for hit in result["hits"]:
                if hit["hit_id"] == hit_id:
                    return hit.get("risk_categories", [])
        return []

    # --- Module 3 (ephemeral ids: match by headline content) ---

    async def _module3_themes(self, entity_id: str, headline: str) -> list[str]:
        findings = await self._read_live_module3_findings(entity_id)
        if findings is None:
            findings = self._read_fixture_module3_findings(entity_id)
        for finding in findings:
            if finding.get("source_hit", {}).get("headline") == headline:
                return finding.get("themes", [])
        return []

    async def _read_live_module3_findings(self, entity_id: str) -> list[dict] | None:
        url = f"{self._module3_base_url}/api/entities/{entity_id}/adverse-media-findings"
        try:
            async with httpx.AsyncClient(timeout=self._module3_timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException):
            return None
        return response.json().get("findings", [])

    def _read_fixture_module3_findings(self, entity_id: str) -> list[dict]:
        data = json.loads(MODULE3_FIXTURES_PATH.read_text(encoding="utf-8"))
        return [f for f in data if f["entity_id"] == entity_id]


theme_enrichment_service = ThemeEnrichmentService()
