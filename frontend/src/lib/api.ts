const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
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
