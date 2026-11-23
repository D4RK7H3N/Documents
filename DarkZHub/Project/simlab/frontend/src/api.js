import axios from "axios";

// Base URL comes from VITE_API_URL (set by docker-compose); plain local
// development falls back to the backend's default port.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8003",
  timeout: 15000,
});

/** GET /api/engines/ -> [{name, version, param_schema}] */
export async function fetchEngines() {
  const { data } = await api.get("/api/engines/");
  return data;
}

/** POST /api/experiments/ -> created experiment (id, status, ...) */
export async function createExperiment(engine, params) {
  const { data } = await api.post("/api/experiments/", { engine, params });
  return data;
}

/** GET /api/experiments/ -> lightweight experiment list (History page) */
export async function fetchExperiments() {
  const { data } = await api.get("/api/experiments/");
  return data;
}

/** GET /api/experiments/{id}/ -> experiment with status/result */
export async function fetchExperiment(id) {
  const { data } = await api.get(`/api/experiments/${id}/`);
  return data;
}

/** GET /api/sweeps/ -> lightweight sweep list */
export async function fetchSweeps() {
  const { data } = await api.get("/api/sweeps/");
  return data;
}

/** GET /api/sweeps/{id}/ -> sweep with progress, axes, cells */
export async function fetchSweep(id) {
  const { data } = await api.get(`/api/sweeps/${id}/`);
  return data;
}

/** POST /api/sweeps/ -> created sweep (id, status, progress, cells...) */
export async function createSweep(payload) {
  const { data } = await api.post("/api/sweeps/", payload);
  return data;
}
