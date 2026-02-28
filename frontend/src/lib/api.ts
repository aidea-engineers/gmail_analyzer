import { supabase } from "@/lib/supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  if (!supabase) return headers;
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      headers["Authorization"] = `Bearer ${session.access_token}`;
    }
  } catch {
    // Supabase未設定時（ローカル開発）は何も付与しない
  }
  return headers;
}

async function fetchAPI<T>(path: string, init?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const mergedHeaders = {
    ...authHeaders,
    ...(init?.headers || {}),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
    headers: mergedHeaders,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

/* Dashboard */
export function getKPIs(period: string) {
  return fetchAPI<import("@/types").KPIs>(
    `/api/dashboard/kpis?period=${encodeURIComponent(period)}`
  );
}

export function getCharts(period: string, granularity = "daily") {
  return fetchAPI<import("@/types").ChartsResponse>(
    `/api/dashboard/charts?period=${encodeURIComponent(period)}&granularity=${granularity}`
  );
}

export function getMonthlySummary(months = 6) {
  return fetchAPI<import("@/types").MonthlySummary[]>(
    `/api/dashboard/monthly-summary?months=${months}`
  );
}

/* Search */
export function getFilters() {
  return fetchAPI<import("@/types").SearchFilters>("/api/search/filters");
}

export function getListings(params: Record<string, string>) {
  const qs = new URLSearchParams(params).toString();
  return fetchAPI<import("@/types").ListingsResponse>(
    `/api/search/listings?${qs}`
  );
}

export function getExportURL(params: Record<string, string>) {
  const qs = new URLSearchParams(params).toString();
  return `${API_BASE}/api/search/export?${qs}`;
}

/* Fetch */
export function getFetchStatus() {
  return fetchAPI<import("@/types").FetchStatus>("/api/fetch/status");
}

export function getFetchLogs(limit = 10) {
  return fetchAPI<{ logs: import("@/types").FetchLog[] }>(
    `/api/fetch/logs?limit=${limit}`
  );
}

export function startFullPipeline() {
  return fetchAPI<{ job_id: string }>("/api/fetch/full-pipeline", {
    method: "POST",
  });
}

export function startAIOnly() {
  return fetchAPI<{ job_id: string }>("/api/fetch/ai-only", {
    method: "POST",
  });
}

export function insertMockData(count = 150) {
  return fetchAPI<{ inserted: number }>(`/api/fetch/mock?count=${count}`, {
    method: "POST",
  });
}

export function deleteAllData() {
  return fetchAPI<{ message: string }>("/api/fetch/data", {
    method: "DELETE",
  });
}

export function getProgressURL(jobId: string) {
  return `${API_BASE}/api/fetch/progress/${jobId}`;
}

/* Settings */
export function getSettings() {
  return fetchAPI<import("@/types").Settings>("/api/settings");
}

export function updateSettings(data: import("@/types").SettingsUpdate) {
  return fetchAPI<{ message: string }>("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

/* Engineers */
export function getEngineerStats() {
  return fetchAPI<import("@/types").EngineerStats>("/api/engineers/stats");
}

export function getEngineerFilters() {
  return fetchAPI<import("@/types").EngineerFilters>("/api/engineers/filters");
}

export function getEngineers(params: Record<string, string>) {
  const qs = new URLSearchParams(params).toString();
  return fetchAPI<import("@/types").EngineersResponse>(
    `/api/engineers/list?${qs}`
  );
}

export function getEngineerDetail(id: number) {
  return fetchAPI<import("@/types").EngineerDetail>(`/api/engineers/${id}`);
}

export function createEngineer(data: Record<string, unknown>) {
  return fetchAPI<{ id: number; message: string }>("/api/engineers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function updateEngineer(id: number, data: Record<string, unknown>) {
  return fetchAPI<{ message: string }>(`/api/engineers/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function deleteEngineer(id: number) {
  return fetchAPI<{ message: string }>(`/api/engineers/${id}`, {
    method: "DELETE",
  });
}

export function getEngineerExportURL(params: Record<string, string>) {
  const qs = new URLSearchParams(params).toString();
  return `${API_BASE}/api/engineers/export?${qs}`;
}

export async function importEngineersCsv(file: File) {
  const authHeaders = await getAuthHeaders();
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/engineers/import-csv`, {
    method: "POST",
    body: formData,
    headers: authHeaders,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<import("@/types").CsvImportResult>;
}

export function createAssignment(engineerId: number, data: Record<string, unknown>) {
  return fetchAPI<{ id: number; message: string }>(
    `/api/engineers/${engineerId}/assignments`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
}

export function deleteAssignment(assignmentId: number) {
  return fetchAPI<{ message: string }>(
    `/api/engineers/assignments/${assignmentId}`,
    { method: "DELETE" }
  );
}

/* Matching */
export function getMatchingStats() {
  return fetchAPI<import("@/types").MatchingStats>("/api/matching/stats");
}

export function getEngineersForListing(listingId: number, limit = 20) {
  return fetchAPI<{ matches: import("@/types").EngineerMatchResult[] }>(
    `/api/matching/engineers-for-listing/${listingId}?limit=${limit}`
  );
}

export function getListingsForEngineer(engineerId: number, limit = 20) {
  return fetchAPI<{ matches: import("@/types").ListingMatchResult[] }>(
    `/api/matching/listings-for-engineer/${engineerId}?limit=${limit}`
  );
}

export function createProposal(data: {
  engineer_id: number;
  listing_id: number;
  score: number;
  notes?: string;
}) {
  return fetchAPI<{ id: number; message: string }>("/api/matching/proposals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function updateProposal(
  proposalId: number,
  data: { status: string; notes?: string }
) {
  return fetchAPI<{ message: string }>(
    `/api/matching/proposals/${proposalId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
}

export function deleteProposal(proposalId: number) {
  return fetchAPI<{ message: string }>(
    `/api/matching/proposals/${proposalId}`,
    { method: "DELETE" }
  );
}

export function getProposals(params: Record<string, string>) {
  const qs = new URLSearchParams(params).toString();
  return fetchAPI<{ proposals: import("@/types").MatchProposal[] }>(
    `/api/matching/proposals?${qs}`
  );
}

export function getEngineersBrief() {
  return fetchAPI<import("@/types").EngineerBrief[]>(
    "/api/matching/engineers-brief"
  );
}

/* Import (Phase 2) */
export async function importDataCsv(type: "employees" | "assignments" | "companies", file: File) {
  const authHeaders = await getAuthHeaders();
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/import/${type}`, {
    method: "POST",
    body: formData,
    headers: authHeaders,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<import("@/types").CsvImportResult>;
}
