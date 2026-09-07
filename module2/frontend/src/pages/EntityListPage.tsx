import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { EntityScreeningStatus, SourceStatusBadge } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

const FILTERS: { value: SourceStatusBadge | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "hits_found", label: "Hits Found" },
  { value: "needs_refresh", label: "Needs Refresh" },
  { value: "source_unavailable", label: "Source Unavailable" },
  { value: "clear", label: "Clear" },
];

export function EntityListPage() {
  const [entities, setEntities] = useState<EntityScreeningStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<SourceStatusBadge | "all">("all");

  useEffect(() => {
    api
      .listEntities()
      .then(setEntities)
      .catch((err) => setError(String(err.message ?? err)));
  }, []);

  const visible = useMemo(() => {
    if (!entities) return [];
    return entities.filter((e) => {
      const matchesSearch = e.legal_name.toLowerCase().includes(search.toLowerCase());
      const matchesFilter = filter === "all" || e.badge === filter;
      return matchesSearch && matchesFilter;
    });
  }, [entities, search, filter]);

  if (error) return <div className="panel error-panel">Failed to load entities: {error}</div>;
  if (!entities) return <div className="panel">Loading entities…</div>;

  return (
    <div>
      <div className="list-controls">
        <input
          className="search-input"
          placeholder="Search by legal name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-chips">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              className={`chip ${filter === f.value ? "chip-active" : ""}`}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <table className="entity-table">
        <thead>
          <tr>
            <th>Entity</th>
            <th>Type</th>
            <th>Status</th>
            <th>Total Hits</th>
            <th>Sources Queried</th>
            <th>Last Queried</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((entity) => (
            <tr key={entity.entity_id}>
              <td>
                <Link to={`/entities/${encodeURIComponent(entity.entity_id)}`}>{entity.legal_name}</Link>
              </td>
              <td className="capitalize">{entity.entity_type}</td>
              <td>
                <StatusBadge badge={entity.badge} />
              </td>
              <td>{entity.total_hits}</td>
              <td>
                {entity.sources_queried}
                {entity.sources_unavailable > 0 && (
                  <span className="unavailable-note"> ({entity.sources_unavailable} unavailable)</span>
                )}
              </td>
              <td>{entity.last_queried_at ? new Date(entity.last_queried_at).toLocaleString() : "Never"}</td>
            </tr>
          ))}
          {visible.length === 0 && (
            <tr>
              <td colSpan={6} className="empty-row">
                No entities match your search/filter.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
