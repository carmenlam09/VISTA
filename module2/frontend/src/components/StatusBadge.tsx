import type { SourceStatusBadge } from "../api/types";

const BADGE_META: Record<SourceStatusBadge, { label: string; className: string }> = {
  clear: { label: "Clear", className: "badge badge-clear" },
  hits_found: { label: "Hits Found", className: "badge badge-hits" },
  needs_refresh: { label: "Needs Refresh", className: "badge badge-refresh" },
  source_unavailable: { label: "Source Unavailable", className: "badge badge-unavailable" },
};

export function StatusBadge({ badge }: { badge: SourceStatusBadge }) {
  const meta = BADGE_META[badge];
  return <span className={meta.className}>{meta.label}</span>;
}
