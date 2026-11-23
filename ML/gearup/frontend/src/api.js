const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8010/api";

const TOKEN_KEY = "gearup_access";
const REFRESH_KEY = "gearup_refresh";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const getRefreshToken = () => localStorage.getItem(REFRESH_KEY);
export const setTokens = ({ access, refresh }) => {
  localStorage.setItem(TOKEN_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
};
export const clearTokens = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
};

export const cartChanged = () => window.dispatchEvent(new Event("gearup:cart"));

function messageFrom(status, data) {
  if (typeof data === "string" && data) return data;
  if (data?.error) return data.error;
  if (data?.detail) return data.detail;
  const first = data && Object.values(data)[0];
  if (Array.isArray(first)) return first.join(" ");
  if (typeof first === "string") return first;
  return `Request failed (HTTP ${status})`;
}

export class ApiError extends Error {
  constructor(status, data) {
    super(messageFrom(status, data));
    this.status = status;
    this.data = data;
  }
}

export async function api(path, { method = "GET", body, auth = true } = {}) {
  const buildHeaders = (token) => {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth && token) headers.Authorization = `Bearer ${token}`;
    return headers;
  };

  const doFetch = (token) =>
    fetch(`${API_URL}${path}`, {
      method,
      headers: buildHeaders(token),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

  let res = await doFetch(getToken());

  // One transparent retry after refreshing an expired access token.
  if (res.status === 401 && auth && getRefreshToken()) {
    try {
      const r = await fetch(`${API_URL}/auth/token/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: getRefreshToken() }),
      });
      if (r.ok) {
        const d = await r.json();
        setTokens({ access: d.access });
        res = await doFetch(d.access);
      } else {
        clearTokens();
      }
    } catch {
      clearTokens();
    }
  }

  const data = res.status === 204 ? null : await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

export const peso = (value) =>
  `₱${Number(value ?? 0).toLocaleString("en-PH", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
