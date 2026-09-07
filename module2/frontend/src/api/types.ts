export type EntityType = "vendor" | "director" | "shareholder" | "ubo";

export interface IdNumber {
  type: string;
  value: string;
}

export interface RelatedEntity {
  entity_id: string;
  relationship: string;
}

export interface EntityProfile {
  entity_id: string;
  entity_type: EntityType;
  legal_name: string;
  aliases: string[];
  id_numbers: IdNumber[];
  nationality: string | null;
  date_of_incorporation_or_birth: string | null;
  related_entities: RelatedEntity[];
}

export type SourceName = "ctos" | "netreveal" | "prior_kyv" | "adverse_news" | "public_records";

export type RiskCategory =
  | "financial_crime"
  | "sanctions"
  | "fraud"
  | "regulatory_breach"
  | "tax"
  | "esg"
  | "operational";

export type SourceStatus = "ok" | "error" | "timeout";
export type MatchConfidence = "high" | "medium" | "low";

export interface ScreeningHit {
  hit_id: string;
  title: string;
  description: string;
  hit_date: string | null;
  risk_categories: RiskCategory[];
  confidence: MatchConfidence;
  raw: Record<string, unknown>;
}

export interface ScreeningResult {
  result_id: string;
  entity_id: string;
  source: SourceName;
  status: SourceStatus;
  queried_at: string;
  hit_count: number;
  risk_categories: RiskCategory[];
  match_confidence: MatchConfidence | null;
  hits: ScreeningHit[];
  source_metadata: Record<string, unknown>;
  error_message: string | null;
  is_archived: boolean;
}

export type SourceStatusBadge = "clear" | "hits_found" | "needs_refresh" | "source_unavailable";

export interface EntityScreeningStatus {
  entity_id: string;
  legal_name: string;
  entity_type: EntityType;
  badge: SourceStatusBadge;
  total_hits: number;
  sources_queried: number;
  sources_unavailable: number;
  last_queried_at: string | null;
}

export interface AggregationResponse {
  entity_id: string;
  results: ScreeningResult[];
  requested_sources: SourceName[];
  succeeded_sources: SourceName[];
  failed_sources: SourceName[];
}

export interface SummaryFinding {
  theme: RiskCategory;
  source: SourceName;
  statement: string;
  severity: string;
}

export interface ScreeningSummary {
  entity_id: string;
  narrative: string;
  findings: SummaryFinding[];
  missing_or_inconclusive: string[];
  generated_at: string;
  generator: string;
}

export interface AuditLogEntry {
  id: string;
  actor_id: string;
  actor_role: string;
  action: string;
  entity_id: string;
  sources: SourceName[];
  detail: Record<string, unknown>;
  created_at: string;
}

export const SOURCE_LABELS: Record<SourceName, string> = {
  ctos: "CTOS",
  netreveal: "NetReveal",
  prior_kyv: "Prior KYV Reviews",
  adverse_news: "Adverse News",
  public_records: "Public Records",
};

export const RISK_CATEGORY_LABELS: Record<RiskCategory, string> = {
  financial_crime: "Financial Crime",
  sanctions: "Sanctions",
  fraud: "Fraud",
  regulatory_breach: "Regulatory Breach",
  tax: "Tax",
  esg: "ESG",
  operational: "Operational",
};
