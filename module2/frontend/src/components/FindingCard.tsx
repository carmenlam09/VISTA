import { RISK_CATEGORY_LABELS, SOURCE_LABELS, type SummaryFinding } from "../api/types";

export function FindingCard({ finding }: { finding: SummaryFinding }) {
  return (
    <li className={`finding finding-${finding.severity}`}>
      <div className="finding-meta">
        <span className={`severity-dot severity-${finding.severity}`} aria-hidden="true" />
        <span className="finding-theme">{RISK_CATEGORY_LABELS[finding.theme] ?? finding.theme}</span>
        <span className="finding-source">source: {SOURCE_LABELS[finding.source] ?? finding.source}</span>
      </div>
      <p className="finding-statement">{finding.statement}</p>
    </li>
  );
}
