/** App shell — sidebar + topbar. */
import { api } from "./api.js";
import { requireSession, logout } from "./auth.js";
import { bindModalDismiss, closeModal, openModal } from "./components/modal.js";
import { toast } from "./ui.js";

const NAV = [
  { id: "home", href: "/", icon: "bi-grid-1x2", label: "Dashboard" },
  { id: "projectos", href: "/projectos", icon: "bi-folder2-open", label: "Base de projectos" },
  { id: "avaliacoes", href: "/avaliacoes", icon: "bi-archive", label: "Arquivo" },
  { id: "relatorios", href: "/relatorios", icon: "bi-file-earmark-bar-graph", label: "Relatorios" },
  { id: "anexos", href: "/anexos", icon: "bi-paperclip", label: "Anexos" },
  { id: "situacao", href: "/situacao", icon: "bi-calendar2-week", label: "Ponto de situacao" },
  { id: "resultados", href: "/dashboard", icon: "bi-speedometer2", label: "Resultados" },
];

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function canAdmin(user) {
  if (!user) return false;
  if (user.role === "admin") return true;
  const perms = user.permissions || [];
  return (
    perms.includes("admin.access") ||
    perms.includes("users.manage") ||
    perms.includes("roles.manage") ||
    perms.includes("catalog.manage") ||
    perms.includes("projectos.manage")
  );
}

function canChangePassword(user) {
  if (!user) return false;
  if (user.role === "admin") return true;
  return (user.permissions || []).includes("account.change_password");
}

function mountPasswordModal(shell, user, { forced = false } = {}) {
  if (!canChangePassword(user) && !forced) return;

  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.id = "modal-change-password";
  backdrop.hidden = true;
  if (forced) backdrop.dataset.forced = "1";
  backdrop.innerHTML = `
    <div class="modal-card" role="dialog" aria-modal="true">
      <div class="modal-head">
        <h3>${forced ? "Alteracao de palavra-passe obrigatoria" : "Alterar palavra-passe"}</h3>
        ${
          forced
            ? ""
            : `<button type="button" class="modal-close" data-close-modal aria-label="Fechar"><i class="bi bi-x-lg"></i></button>`
        }
      </div>
      <form id="password-form">
        <div class="modal-body">
          ${
            forced
              ? `<p class="panel-hint" style="margin-bottom:12px">Por seguranca, deve definir uma nova palavra-passe antes de continuar.</p>`
              : ""
          }
          <div class="field-grid">
            <label class="field full"><span>Palavra-passe actual</span><input id="pw_current" type="password" required autocomplete="current-password" /></label>
            <label class="field"><span>Nova palavra-passe</span><input id="pw_new" type="password" required minlength="8" autocomplete="new-password" /></label>
            <label class="field"><span>Confirmar</span><input id="pw_confirm" type="password" required minlength="8" autocomplete="new-password" /></label>
          </div>
        </div>
        <div class="modal-foot">
          <button type="submit" class="btn btn-primary compact">Guardar</button>
          ${
            forced
              ? ""
              : `<button type="button" class="btn btn-outline compact" data-close-modal>Cancelar</button>`
          }
        </div>
      </form>
    </div>`;
  document.body.appendChild(backdrop);
  if (!forced) bindModalDismiss(backdrop);

  shell.querySelector("#btn-change-password")?.addEventListener("click", () => {
    backdrop.querySelector("#password-form").reset();
    openModal(backdrop);
  });

  backdrop.querySelector("#password-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const current = backdrop.querySelector("#pw_current").value;
    const next = backdrop.querySelector("#pw_new").value;
    const confirm = backdrop.querySelector("#pw_confirm").value;
    if (next !== confirm) {
      toast("A confirmacao nao coincide.", "error");
      return;
    }
    try {
      await api("/auth/password", {
        method: "PATCH",
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      toast("Palavra-passe actualizada.", "success");
      if (forced) {
        window.location.reload();
        return;
      }
      closeModal(backdrop);
    } catch (err) {
      toast(err.message || "Erro ao alterar palavra-passe", "error");
    }
  });

  if (forced) {
    openModal(backdrop);
  }
}

export async function bootPage({ page, title = "", subtitle = "" } = {}) {
  const user = await requireSession();
  if (!user) return { user: null };

  const app = document.getElementById("app");
  if (!app) throw new Error("Missing #app root");

  app.hidden = false;
  app.querySelector(".boot-loading")?.remove();
  const contentRoot = app.querySelector("#app-content") || app;
  contentRoot.hidden = false;

  const pageTitle = title || document.title;
  const nav = [...NAV];
  if (canAdmin(user)) {
    nav.push({ id: "admin", href: "/admin", icon: "bi-gear", label: "Administracao" });
  }

  const navItems = nav
    .map(
      (n) => `
      <a class="nav-item ${n.id === page ? "active" : ""}" href="${n.href}" data-nav="${n.id}">
        <i class="bi ${n.icon}"></i>
        <span>${n.label}</span>
      </a>`
    )
    .join("");

  const passwordBtn = canChangePassword(user)
    ? `<button type="button" class="icon-btn" id="btn-change-password" title="Alterar palavra-passe" aria-label="Alterar palavra-passe">
         <i class="bi bi-key"></i>
       </button>`
    : "";

  const shell = document.createElement("div");
  shell.className = "app-shell ready";
  shell.innerHTML = `
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-brand">
        <img src="/assets/logo.png" alt="Logo" />
        <strong>CTD Portal</strong>
      </div>
      <nav class="sidebar-nav">${navItems}</nav>
      <div class="sidebar-foot">
        ${
          canChangePassword(user)
            ? `<button type="button" class="nav-item icon-only" id="btn-change-password-side" title="Alterar palavra-passe" aria-label="Alterar palavra-passe">
                 <i class="bi bi-key"></i>
               </button>`
            : ""
        }
        <button type="button" class="nav-item logout-btn icon-only" id="btn-logout" title="Sair" aria-label="Sair">
          <i class="bi bi-box-arrow-right"></i>
        </button>
      </div>
    </aside>
    <div class="shell-main">
      <header class="shell-top">
        <button type="button" class="icon-btn mobile-only" id="btn-sidebar" aria-label="Menu">
          <i class="bi bi-list"></i>
        </button>
        <div class="shell-titles">
          <h1>${escapeHtml(pageTitle)}</h1>
          ${subtitle ? `<p>${escapeHtml(subtitle)}</p>` : ""}
        </div>
        <div class="shell-user">
          <div class="notif-wrap">
            <button type="button" class="icon-btn" id="btn-notifications" title="Notificacoes" aria-label="Notificacoes">
              <i class="bi bi-bell"></i>
              <span class="notif-badge" id="notif-badge" hidden>0</span>
            </button>
            <div class="notif-dropdown" id="notif-dropdown" hidden>
              <div class="notif-dropdown-head">
                <div class="notif-dropdown-title">
                  <i class="bi bi-bell-fill"></i>
                  <strong>Notificacoes</strong>
                </div>
                <button type="button" class="btn btn-ghost compact" id="btn-notif-read-all">
                  Marcar lidas
                </button>
              </div>
              <div class="notif-dropdown-list" id="notif-list">
                <div class="notif-empty">
                  <i class="bi bi-inbox"></i>
                  <p>A carregar...</p>
                </div>
              </div>
            </div>
          </div>
          <span class="user-avatar" title="${escapeHtml(user.name)}"><i class="bi bi-person"></i></span>
          ${passwordBtn}
          <button type="button" class="icon-btn" id="btn-logout-top" title="Sair" aria-label="Sair">
            <i class="bi bi-box-arrow-right"></i>
          </button>
        </div>
      </header>
      <main class="shell-content" id="shell-content"></main>
    </div>
    <div class="sidebar-backdrop" id="sidebar-backdrop" hidden></div>
  `;

  const content = shell.querySelector("#shell-content");
  while (contentRoot.firstChild) content.appendChild(contentRoot.firstChild);
  app.replaceWith(shell);
  document.body.classList.add("app-body");

  const sidebar = shell.querySelector("#sidebar");
  const backdrop = shell.querySelector("#sidebar-backdrop");
  const toggle = () => {
    const open = sidebar.classList.toggle("open");
    backdrop.hidden = !open;
  };
  shell.querySelector("#btn-sidebar")?.addEventListener("click", toggle);
  backdrop?.addEventListener("click", toggle);

  const doLogout = async () => {
    try {
      await logout();
    } catch {
      /* leave */
    }
    window.location.replace("/login");
  };
  shell.querySelector("#btn-logout")?.addEventListener("click", doLogout);
  shell.querySelector("#btn-logout-top")?.addEventListener("click", doLogout);

  mountPasswordModal(shell, user, { forced: Boolean(user.must_change_password) });
  if (user.must_change_password) {
    shell.querySelector(".sidebar-nav")?.setAttribute("aria-disabled", "true");
    shell.querySelectorAll(".sidebar-nav a, .shell-titles a").forEach((a) => {
      a.addEventListener(
        "click",
        (ev) => {
          ev.preventDefault();
          toast("Altere a palavra-passe para continuar.", "error");
        },
        true
      );
    });
  }
  shell.querySelector("#btn-change-password-side")?.addEventListener("click", () => {
    const modal = document.getElementById("modal-change-password");
    if (modal) {
      modal.querySelector("#password-form")?.reset();
      openModal(modal);
    }
  });

  mountNotifications(shell);

  return { user, shell };
}

async function mountNotifications(shell) {
  const badge = shell.querySelector("#notif-badge");
  const dropdown = shell.querySelector("#notif-dropdown");
  const list = shell.querySelector("#notif-list");
  const btn = shell.querySelector("#btn-notifications");

  async function refresh() {
    try {
      const data = await api("/notifications");
      const unread = Number(data.unread || 0);
      if (badge) {
        badge.hidden = unread <= 0;
        badge.textContent = unread > 9 ? "9+" : String(unread);
      }
      const rows = data.notifications || [];
      if (!list) return;
      if (!rows.length) {
        list.innerHTML = `
          <div class="notif-empty">
            <i class="bi bi-bell-slash"></i>
            <p>Sem notificacoes</p>
            <span>Quando houver avisos, aparecem aqui.</span>
          </div>`;
        return;
      }
      list.innerHTML = rows
        .map((n) => {
          const when = n.created_at
            ? new Date(n.created_at).toLocaleString("pt-MZ", {
                day: "2-digit",
                month: "short",
                hour: "2-digit",
                minute: "2-digit",
              })
            : "";
          return `
        <a class="notif-item ${n.lida ? "" : "is-unread"}" href="${escapeHtml(n.link || "#")}" data-id="${n.id}">
          <span class="notif-item-dot" aria-hidden="true"></span>
          <span class="notif-item-body">
            <strong>${escapeHtml(n.titulo)}</strong>
            <span class="notif-item-text">${escapeHtml(n.corpo || "")}</span>
            ${when ? `<time class="notif-item-time">${escapeHtml(when)}</time>` : ""}
          </span>
        </a>`;
        })
        .join("");
      list.querySelectorAll(".notif-item").forEach((el) => {
        el.addEventListener("click", async () => {
          const id = el.dataset.id;
          try {
            await api(`/notifications/${id}/read`, { method: "POST", body: "{}" });
          } catch {
            /* ignore */
          }
        });
      });
    } catch {
      /* ignore */
    }
  }

  btn?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!dropdown) return;
    dropdown.hidden = !dropdown.hidden;
    if (!dropdown.hidden) refresh();
  });
  shell.querySelector("#btn-notif-read-all")?.addEventListener("click", async (e) => {
    e.stopPropagation();
    try {
      await api("/notifications/read-all", { method: "POST", body: "{}" });
      await refresh();
    } catch (err) {
      toast(err.message || "Erro", "error");
    }
  });
  document.addEventListener("click", () => {
    if (dropdown) dropdown.hidden = true;
  });
  dropdown?.addEventListener("click", (e) => e.stopPropagation());
  refresh();
}
