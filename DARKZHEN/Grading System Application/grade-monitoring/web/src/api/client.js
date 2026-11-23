const BASE = "/api/v1";

const storage = {
  get access() {
    return localStorage.getItem("access");
  },
  get refresh() {
    return localStorage.getItem("refresh");
  },
  set(access, refresh) {
    localStorage.setItem("access", access);
    if (refresh) localStorage.setItem("refresh", refresh);
  },
  clear() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
  },
};

export class ApiError extends Error {
  constructor(status, data) {
    const err = data?.error;
    super(err?.message || (status === 0 ? "Network error." : "Request failed."));
    this.status = status;
    this.code = err?.code || "error";
    this.details = err?.details;
  }
}

let onSessionExpired = () => {};

export function setSessionExpiredHandler(handler) {
  onSessionExpired = handler;
}

async function tryRefresh() {
  const refresh = storage.refresh;
  if (!refresh) return false;
  try {
    const res = await fetch(`${BASE}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    storage.set(data.access, data.refresh || refresh);
    return true;
  } catch {
    return false;
  }
}

export async function api(path, { method = "GET", body, auth = true } = {}) {
  const doFetch = () => {
    const headers = { "Content-Type": "application/json" };
    if (auth && storage.access) headers.Authorization = `Bearer ${storage.access}`;
    return fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let res = await doFetch();
  if (res.status === 401 && auth && !path.startsWith("/auth/")) {
    if (await tryRefresh()) {
      res = await doFetch();
    } else {
      storage.clear();
      onSessionExpired();
      throw new ApiError(401, { error: { code: "not_authenticated", message: "Session expired. Please log in again." } });
    }
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

export async function apiForm(path, { method = "POST", body } = {}) {
  const doFetch = () => {
    const headers = {};
    if (storage.access) headers.Authorization = `Bearer ${storage.access}`;
    return fetch(`${BASE}${path}`, { method, headers, body });
  };

  let res = await doFetch();
  if (res.status === 401) {
    if (await tryRefresh()) {
      res = await doFetch();
    } else {
      storage.clear();
      onSessionExpired();
      throw new ApiError(401, { error: { code: "not_authenticated", message: "Session expired. Please log in again." } });
    }
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

export const profileApi = {
  update(details) {
    return api("/me/", { method: "PATCH", body: details });
  },
  uploadAvatar(file) {
    const body = new FormData();
    body.append("avatar", file, file.name);
    return apiForm("/me/avatar/", { method: "POST", body });
  },
  removeAvatar() {
    return api("/me/avatar/", { method: "DELETE" });
  },
};

export const authApi = {
  async login(username, password) {
    const res = await fetch(`${BASE}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new ApiError(res.status, data);
    storage.set(data.access, data.refresh);
    return data;
  },
  async logout() {
    const refresh = storage.refresh;
    if (refresh) {
      await api("/auth/logout/", { method: "POST", body: { refresh }, auth: true }).catch(() => {});
    }
    storage.clear();
  },
  async changePassword(currentPassword, newPassword) {
    return api("/auth/change-password/", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
    });
  },
  me() {
    return api("/me/");
  },
  hasSession() {
    return Boolean(storage.refresh);
  },
  clearSession() {
    storage.clear();
  },
};
