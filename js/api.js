/** HTTP client — credentials (cookie) + JSON. */

const API_BASE = "/api/v1";

export async function api(path, options = {}) {
  const headers = {
    Accept: "application/json",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
    headers,
  });

  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) {
    const err = new Error("Resposta invalida da API (esperado JSON). Reinicie o servidor.");
    err.status = res.status || 500;
    err.code = "INVALID_RESPONSE";
    throw err;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data?.error?.message || res.statusText || "Erro na API");
    err.status = res.status;
    err.code = data?.error?.code;
    err.data = data;
    throw err;
  }
  return data;
}

/** Multipart upload — do not set Content-Type (browser sets boundary). */
export async function apiForm(path, formData, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    method: options.method || "POST",
    body: formData,
    headers: {
      Accept: "application/json",
      ...(options.headers || {}),
    },
  });

  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) {
    const err = new Error("Resposta invalida da API (esperado JSON). Reinicie o servidor.");
    err.status = res.status || 500;
    err.code = "INVALID_RESPONSE";
    throw err;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data?.error?.message || res.statusText || "Erro na API");
    err.status = res.status;
    err.code = data?.error?.code;
    err.data = data;
    throw err;
  }
  return data;
}

export function formatBytes(n) {
  const v = Number(n) || 0;
  if (v < 1024) return `${v} B`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`;
  return `${(v / (1024 * 1024)).toFixed(1)} MB`;
}
