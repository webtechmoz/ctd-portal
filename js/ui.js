/** UI helpers — toasts, spinners. */

export function toast(message, type = "info") {
  const icons = {
    info: "bi-info-circle",
    success: "bi-check-circle",
    error: "bi-x-circle",
    warning: "bi-exclamation-triangle",
  };
  document.querySelectorAll(".toast").forEach((el) => el.remove());
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<i class="bi ${icons[type] || icons.info}"></i><span></span>`;
  el.querySelector("span").textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

export function spinnerHtml(label = "A carregar...") {
  return `
    <div class="loader-block" role="status" aria-live="polite">
      <div class="spinner" aria-hidden="true"></div>
      <p>${label}</p>
    </div>`;
}

export function setLoading(el, label = "A carregar...") {
  if (!el) return;
  el.innerHTML = spinnerHtml(label);
}

export function bindLogout(btnId = "btn-logout") {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const { logout } = await import("./auth.js");
    try {
      await logout();
    } catch {
      // still redirect
    }
    window.location.replace("/login");
  });
}
