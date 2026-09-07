import type {
  AggregationResponse,
  AuditLogEntry,
  EntityProfile,
  EntityScreeningStatus,
  ScreeningResult,
  ScreeningSummary,
  SourceName,
} from "./types";

export type Role = "reviewer" | "admin";

let currentActor = { userId: "demo-reviewer", role: "reviewer" as Role };

export function setActor(userId: string, role: Role): void {
  currentActor = { userId, role };
}

export function getActor(): { userId: string; role: Role } {
  return currentActor;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": currentActor.userId,
      "X-User-Role": currentActor.role,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? `Request to ${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

const entityPath = (entityId: string) => `/api/entities/${encodeURIComponent(entityId)}`;

export const api = {
  listEntities: () => request<EntityScreeningStatus[]>("/api/entities"),

  getEntity: (entityId: string) => request<EntityProfile>(entityPath(entityId)),

  getCachedResults: (entityId: string) => request<ScreeningResult[]>(`${entityPath(entityId)}/screening`),

  triggerAggregation: (entityId: string, sources?: SourceName[]) =>
    request<AggregationResponse>(`${entityPath(entityId)}/screening/query${queryString(sources)}`, {
      method: "POST",
    }),

  refreshSource: (entityId: string, source: SourceName) =>
    request<AggregationResponse>(`${entityPath(entityId)}/screening/refresh${queryString([source])}`, {
      method: "POST",
    }),

  getSummary: (entityId: string) => request<ScreeningSummary>(`${entityPath(entityId)}/summary`),

  getAuditLog: (entityId: string) => request<AuditLogEntry[]>(`${entityPath(entityId)}/audit`),
};

function queryString(sources?: SourceName[]): string {
  if (!sources || sources.length === 0) return "";
  const params = new URLSearchParams();
  for (const source of sources) params.append("sources", source);
  return `?${params.toString()}`;
}
