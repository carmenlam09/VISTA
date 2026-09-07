import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { EntityProfile, ScreeningResult, ScreeningSummary, SourceName } from "../api/types";
import { SOURCE_LABELS } from "../api/types";
import { SourceSection } from "../components/SourceSection";
import { SummaryPanel } from "../components/SummaryPanel";

const SOURCES: SourceName[] = ["ctos", "netreveal", "prior_kyv", "adverse_news", "public_records"];

export function EntityDetailPage() {
  const { entityId: rawEntityId } = useParams<{ entityId: string }>();
  const entityId = decodeURIComponent(rawEntityId ?? "");

  const [entity, setEntity] = useState<EntityProfile | null>(null);
  const [results, setResults] = useState<ScreeningResult[]>([]);
  const [summary, setSummary] = useState<ScreeningSummary | null>(null);
  const [activeTab, setActiveTab] = useState<SourceName>("ctos");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [refreshingSource, setRefreshingSource] = useState<SourceName | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [entityData, cached] = await Promise.all([api.getEntity(entityId), api.getCachedResults(entityId)]);
      setEntity(entityData);
      setResults(cached);
      if (cached.length > 0) {
        setSummary(await api.getSummary(entityId));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [entityId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  async function runScreening() {
    setRunning(true);
    setError(null);
    try {
      const aggregation = await api.triggerAggregation(entityId);
      setResults(aggregation.results);
      setSummary(await api.getSummary(entityId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  async function refreshSource(source: SourceName) {
    setRefreshingSource(source);
    setError(null);
    try {
      const aggregation = await api.refreshSource(entityId, source);
      const refreshed = aggregation.results[0];
      setResults((prev) => [...prev.filter((r) => r.source !== source), refreshed]);
      setSummary(await api.getSummary(entityId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRefreshingSource(null);
    }
  }

  if (loading) return <div className="panel">Loading entity…</div>;
  if (error && !entity) return <div className="panel error-panel">{error}</div>;
  if (!entity) return null;

  const resultBySource = Object.fromEntries(results.map((r) => [r.source, r])) as Partial<
    Record<SourceName, ScreeningResult>
  >;

  return (
    <div>
      <Link to="/" className="back-link">
        ← Back to entity list
      </Link>

      <div className="entity-header">
        <div>
          <h1>{entity.legal_name}</h1>
          <div className="entity-subtitle">
            <span className="capitalize">{entity.entity_type}</span>
            {entity.nationality && <span> · {entity.nationality}</span>}
            {entity.id_numbers.map((id) => (
              <span key={id.value}>
                {" "}
                · {id.type}: {id.value}
              </span>
            ))}
          </div>
          {entity.related_entities.length > 0 && (
            <div className="related-entities">
              Related:{" "}
              {entity.related_entities.map((rel, i) => (
                <span key={rel.entity_id}>
                  {i > 0 && ", "}
                  <Link to={`/entities/${encodeURIComponent(rel.entity_id)}`}>{rel.entity_id}</Link> (
                  {rel.relationship})
                </span>
              ))}
            </div>
          )}
        </div>
        <button className="primary" onClick={runScreening} disabled={running}>
          {running ? "Running screening…" : "Run Screening"}
        </button>
      </div>

      {error && <div className="panel error-panel">{error}</div>}

      <SummaryPanel summary={summary} />

      <div className="source-tabs">
        {SOURCES.map((source) => {
          const result = resultBySource[source];
          const tabBadge = result ? (result.status === "ok" ? result.hit_count : "!") : "–";
          return (
            <button
              key={source}
              className={`tab ${activeTab === source ? "tab-active" : ""}`}
              onClick={() => setActiveTab(source)}
            >
              {SOURCE_LABELS[source]}
              <span className="tab-badge">{tabBadge}</span>
            </button>
          );
        })}
      </div>

      <SourceSection
        result={resultBySource[activeTab]}
        onRefresh={() => refreshSource(activeTab)}
        refreshing={refreshingSource === activeTab}
      />
    </div>
  );
}
