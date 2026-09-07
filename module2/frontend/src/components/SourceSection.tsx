import { SOURCE_LABELS, type ScreeningResult } from "../api/types";

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function SourceSection({
  result,
  onRefresh,
  refreshing,
}: {
  result: ScreeningResult | undefined;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  if (!result) {
    return (
      <div className="panel source-section">
        <div className="source-header">
          <span className="raw-flag">Raw Source Data</span>
          <button onClick={onRefresh} disabled={refreshing}>
            {refreshing ? "Querying…" : "Query source"}
          </button>
        </div>
        <p className="source-empty">Not queried yet.</p>
      </div>
    );
  }

  return (
    <div className="panel source-section">
      <div className="source-header">
        <span className="raw-flag">Raw Source Data</span>
        <div className="source-header-right">
          <span className={`source-status source-status-${result.status}`}>{result.status}</span>
          <span className="source-staleness">queried {timeAgo(result.queried_at)}</span>
          <button onClick={onRefresh} disabled={refreshing}>
            {refreshing ? "Refreshing…" : "Refresh this source"}
          </button>
        </div>
      </div>

      {result.status !== "ok" && <p className="source-error">{result.error_message}</p>}

      {result.status === "ok" && result.hits.length === 0 && <p className="source-empty">No hits found.</p>}

      {result.status === "ok" && result.hits.length > 0 && (
        <ul className="hit-list">
          {result.hits.map((hit) => (
            <li key={hit.hit_id} className="hit">
              <div className="hit-header">
                <strong>{hit.title}</strong>
                <span className={`confidence confidence-${hit.confidence}`}>{hit.confidence} confidence</span>
              </div>
              <p>{hit.description}</p>
              {hit.hit_date && <div className="hit-date">Dated {hit.hit_date}</div>}
            </li>
          ))}
        </ul>
      )}

      <div className="source-metadata-label">Source: {SOURCE_LABELS[result.source]}</div>
    </div>
  );
}
