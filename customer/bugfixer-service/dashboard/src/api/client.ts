import type {
  Me,
  Paginated,
  Project,
  ProjectInput,
  ReportDetail,
  ReportStatus,
  ReportSummary,
  SettingsFlags,
  Stats,
} from "./types";

const configured = (import.meta.env.VITE_API_URL ?? "").trim();
const BASE = (configured || "https://bugfixer.darkzhub.asia").replace(/\/$/, "");

let csrfToken = "";

async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  const response = await fetch(`${BASE}/api/dashboard/auth/csrf/`, { credentials: "include" });
  if (!response.ok) throw new Error(`Could not get CSRF token (${response.status})`);
  const data = (await response.json()) as { csrfToken?: string };
  csrfToken = data.csrfToken ?? "";
  return csrfToken;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (["POST", "PATCH", "PUT", "DELETE"].includes(method)) {
    headers.set("X-CSRFToken", await ensureCsrf());
  }
  const response = await fetch(`${BASE}/api/dashboard${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
  });
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    throw new Error(`API returned non-JSON (${response.status}). Check VITE_API_URL.`);
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // non-JSON error body
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function jsonBody(value: unknown): string {
  return JSON.stringify(value);
}

export interface ReportFilters {
  project?: string;
  status?: string;
  classification?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  ordering?: string;
  limit?: number;
  offset?: number;
}

export const api = {
  auth: {
    csrf: async () => {
      csrfToken = "";
      const token = await ensureCsrf();
      return { detail: "ok", csrfToken: token };
    },
    login: (username: string, password: string) =>
      request<Me>("/auth/login/", { method: "POST", body: jsonBody({ username, password }) }),
    logout: () => request<{ detail: string }>("/auth/logout/", { method: "POST" }),
    me: () => request<Me>("/auth/me/"),
  },
  projects: {
    list: () => request<Project[]>("/projects/"),
    create: (data: ProjectInput) =>
      request<Project>("/projects/", { method: "POST", body: jsonBody(data) }),
    update: (id: number, data: ProjectInput) =>
      request<Project>(`/projects/${id}/`, { method: "PATCH", body: jsonBody(data) }),
    remove: (id: number) => request<void>(`/projects/${id}/`, { method: "DELETE" }),
    rotateKey: (id: number) => request<Project>(`/projects/${id}/rotate-key/`, { method: "POST" }),
  },
  reports: {
    list: (filters: ReportFilters) => {
      const query = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== "") query.set(key, String(value));
      });
      return request<Paginated<ReportSummary>>(`/reports/?${query.toString()}`);
    },
    get: (id: number) => request<ReportDetail>(`/reports/${id}/`),
    requeue: (id: number) => request<ReportDetail>(`/reports/${id}/requeue/`, { method: "POST" }),
    reject: (id: number) => request<ReportDetail>(`/reports/${id}/reject/`, { method: "POST" }),
    approvePr: (id: number) =>
      request<{ result: { opened: number; skipped: number; failed: number }; report: ReportDetail }>(
        `/reports/${id}/approve-pr/`,
        { method: "POST" },
      ),
  },
  stats: () => request<Stats>("/stats/"),
  settings: () => request<SettingsFlags>("/settings/"),
};

export type { ReportStatus };
