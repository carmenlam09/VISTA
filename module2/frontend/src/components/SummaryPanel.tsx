import type { ScreeningSummary } from "../api/types";
import { FindingCard } from "./FindingCard";

export function SummaryPanel({ summary }: { summary: ScreeningSummary | null; }) {
  if (!summary) {
    return <div className="panel summary-panel summary-empty">No AI summary generated yet.</div>;
  }

  return (
    <div className="panel summary-panel">
      <div className="ai-flag">AI-Generated Synthesis — not a raw source record</div>
      <p className="summary-narrative">{summary.narrative}</p>

      {summary.findings.length > 0 && (
        <>
          <h3>Notable Findings</h3>
          <ul className="finding-list">
            {summary.findings.map((finding, i) => (
              <FindingCard key={i} finding={finding} />
            ))}
          </ul>
        </>
      )}

      {summary.missing_or_inconclusive.length > 0 && (
        <>
          <h3>Missing or Inconclusive</h3>
          <ul className="missing-list">
            {summary.missing_or_inconclusive.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </>
      )}

      <div className="summary-footer">
        Generated {new Date(summary.generated_at).toLocaleString()} · {summary.generator}
      </div>
    </div>
  );
}
