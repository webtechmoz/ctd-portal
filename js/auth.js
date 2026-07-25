/** Auth helpers — cookie session via API. */
import { api } from "./api.js";

const LOGOUT_FLAG = "ctd_force_login";

export async function me() {
  return api("/auth/me");
}

export async function login(email, password) {
  sessionStorage.removeItem(LOGOUT_FLAG);
  return api("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout() {
  sessionStorage.setItem(LOGOUT_FLAG, "1");
  try {
    return await api("/auth/logout", { method: "POST" });
  } catch (err) {
    // Still treat as logged out locally
    return { message: "Sessao terminada." };
  }
}

export async function requireSession({ redirectTo = "/login" } = {}) {
  try {
    const data = await me();
    if (!data?.user) {
      window.location.replace(redirectTo);
      return null;
    }
    return data.user;
  } catch (err) {
    if (err.status === 401 || err.status === 403 || err.code === "INVALID_RESPONSE") {
      window.location.replace(redirectTo);
      return null;
    }
    throw err;
  }
}

export async function redirectIfAuthenticated(to = "/") {
  if (sessionStorage.getItem(LOGOUT_FLAG) === "1") {
    sessionStorage.removeItem(LOGOUT_FLAG);
    // Extra logout attempt in case cookie clear raced
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      /* ignore */
    }
    return;
  }
  try {
    await me();
    window.location.replace(to);
  } catch {
    // not logged in — stay
  }
}
