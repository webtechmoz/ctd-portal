/** Admin — utilizadores, perfis, projectos (modais), listas de sistema. */
import { api, apiDownload } from "../api.js";
import { filterByQuery, mountSearchPager, paginate } from "../components/list-kit.js";
import { runProjectImport } from "../components/import-preview.js";
import { bindModalDismiss, closeModal, openModal } from "../components/modal.js";
import { enhanceSelect } from "../components/styled-select.js";
import { bootPage } from "../shell.js";
import { setLoading, toast } from "../ui.js";

const { user } = await bootPage({
  page: "admin",
  title: "Administracao",
  subtitle: "Utilizadores, perfis e projectos",
});

const canAccess =
  user?.role === "admin" ||
  (user?.permissions || []).some((p) =>
    [
      "admin.access",
      "users.manage",
      "roles.manage",
      "projectos.manage",
      "catalog.manage",
      "projectos.delete",
      "projectos.deactivate",
    ].includes(p)
  );
if (!canAccess) {
  toast("Acesso reservado a administradores.", "error");
  window.location.replace("/");
}

const perms = new Set(user?.permissions || []);
const isAdmin = user?.role === "admin";
const canCatalog = () => isAdmin || perms.has("catalog.manage") || perms.has("admin.access") || perms.has("projectos.manage");
const canManageProject = () => isAdmin || perms.has("projectos.manage");

document.getElementById("btn-new-pilar")?.toggleAttribute("hidden", !canManageProject());
document.getElementById("btn-new-user")?.toggleAttribute(
  "hidden",
  !(isAdmin || perms.has("users.manage"))
);
document.getElementById("btn-new-role")?.toggleAttribute(
  "hidden",
  !(isAdmin || perms.has("roles.manage"))
);

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function reEnhance(select) {
  if (!select) return;
  if (select.dataset.enhanced === "1") {
    select.dataset.enhanced = "";
    select.classList.remove("sr-only-select");
    const wrap = select.closest(".styled-select");
    if (wrap) {
      wrap.parentNode.insertBefore(select, wrap);
      wrap.remove();
    }
  }
  enhanceSelect(select);
}

const panels = {
  users: document.getElementById("panel-users"),
  roles: document.getElementById("panel-roles"),
  projectos: document.getElementById("panel-projectos"),
  catalog: document.getElementById("panel-catalog"),
};

const optsBtn = document.getElementById("btn-opts");
const optsMenu = document.getElementById("opts-menu");
optsBtn?.addEventListener("click", (e) => {
  e.stopPropagation();
  optsMenu.classList.toggle("open");
});
document.addEventListener("click", () => optsMenu.classList.remove("open"));

function showPanel(key, { persist = true } = {}) {
  if (!panels[key]) key = "users";
  optsMenu?.querySelectorAll("button").forEach((b) => {
    b.classList.toggle("active", b.dataset.panel === key);
  });
  Object.entries(panels).forEach(([k, el]) => {
    if (el) el.hidden = k !== key;
  });
  optsMenu?.classList.remove("open");
  if (persist) {
    sessionStorage.setItem("admin_panel", key);
    const url = `${window.location.pathname}?panel=${encodeURIComponent(key)}#${key}`;
    history.replaceState(null, "", url);
  }
}

optsMenu?.querySelectorAll("button").forEach((btn) => {
  btn.addEventListener("click", () => showPanel(btn.dataset.panel || "users"));
});

function initialAdminPanel() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("panel");
  const fromHash = (window.location.hash || "").replace(/^#/, "");
  const fromStore = sessionStorage.getItem("admin_panel");
  const key = fromQuery || fromHash || fromStore || "users";
  return panels[key] ? key : "users";
}

showPanel(initialAdminPanel());
window.addEventListener("hashchange", () => {
  const key = (window.location.hash || "").replace(/^#/, "");
  if (panels[key]) showPanel(key);
});
[
  "modal-user",
  "modal-role",
  "modal-catalog-item",
].forEach((id) => bindModalDismiss(document.getElementById(id)));

let rolesCache = [];
let permissionsCache = [];
let usersCache = [];
let pilaresCache = [];
let catalogData = { categories: {}, options: {} };

const usersList = document.getElementById("users-list");
const rolesList = document.getElementById("roles-list");
const adminPilares = document.getElementById("admin-pilares");
const roleSelect = document.getElementById("u_role_id");
const userForm = document.getElementById("user-form");
const roleForm = document.getElementById("role-form");

const usersPager = mountSearchPager(document.getElementById("users-controls"), {
  pageSize: 10,
  placeholder: "Pesquisar nome, email, perfil, estado...",
  onChange: renderUsers,
});
const rolesPager = mountSearchPager(document.getElementById("roles-controls"), {
  pageSize: 10,
  placeholder: "Pesquisar perfil, slug, permissoes...",
  onChange: renderRoles,
});
const pilaresPager = mountSearchPager(document.getElementById("pilares-controls"), {
  pageSize: 10,
  placeholder: "Pesquisar projecto, area, fase, status...",
  onChange: renderPilares,
});

/* ── Users ── */
const canManageUsers = () => isAdmin || perms.has("users.manage");
const canManageRoles = () => isAdmin || perms.has("roles.manage");

function openRoleEditor(role) {
  if (!role) return;
  roleForm.dataset.editId = String(role.id);
  document.getElementById("role-modal-title").textContent = "Editar perfil";
  document.getElementById("r_name").value = role.name;
  document.getElementById("r_slug").value = role.slug;
  document.getElementById("r_slug").disabled = true;
  document.getElementById("r_desc").value = role.description || "";
  renderPermEditor(role.permission_codes || []);
  openModal(document.getElementById("modal-role"));
}

function openUserModal(user = null) {
  const editId = document.getElementById("u_edit_id");
  const title = document.getElementById("user-modal-title");
  const saveBtn = document.getElementById("btn-save-user");
  const pwInput = document.getElementById("u_password");
  const pwLabel = document.getElementById("u_password_label");
  const statusField = document.getElementById("u_status_field");
  const emailInput = document.getElementById("u_email");
  const permsBtn = document.getElementById("btn-edit-user-perms");
  const permHint = document.getElementById("user-perm-hint");

  userForm.reset();
  editId.value = user?.id ? String(user.id) : "";

  if (user) {
    title.textContent = "Editar utilizador";
    saveBtn.textContent = "Actualizar";
    document.getElementById("u_name").value = user.name || "";
    emailInput.value = user.email || "";
    emailInput.readOnly = true;
    document.getElementById("u_password_field").hidden = false;
    pwInput.required = false;
    pwInput.value = "";
    pwLabel.textContent = "Nova password (opcional)";
    statusField.hidden = false;
    document.getElementById("u_status").value = user.status || "active";
    reEnhance(document.getElementById("u_status"));
    document.getElementById("u_send_credentials").checked = false;
    document.getElementById("u_reset_hint").hidden = false;
    const roleId =
      user.role_id ||
      rolesCache.find((r) => r.slug === user.role)?.id ||
      "";
    document.getElementById("u_role_id").value = roleId;
    const role = rolesCache.find((r) => r.id === Number(roleId));
    const count = role?.permission_codes?.length || 0;
    permHint.hidden = false;
    permHint.textContent = role
      ? `Perfil «${role.name}» — ${count} permissao(oes). As permissoes sao do perfil, nao do utilizador individual.`
      : "Seleccione um perfil para gerir permissoes.";
    permsBtn.hidden = !(canManageRoles() && role);
    permsBtn.dataset.roleId = role ? String(role.id) : "";
    syncPasswordOptional();
  } else {
    title.textContent = "Novo utilizador";
    saveBtn.textContent = "Criar";
    emailInput.readOnly = false;
    document.getElementById("u_password_field").hidden = false;
    statusField.hidden = true;
    permHint.hidden = true;
    permsBtn.hidden = true;
    permsBtn.dataset.roleId = "";
    document.getElementById("u_send_credentials").checked = true;
    document.getElementById("u_reset_hint").hidden = true;
    syncPasswordOptional();
  }

  reEnhance(roleSelect);
  openModal(document.getElementById("modal-user"));
}

function syncPasswordOptional() {
  const pwInput = document.getElementById("u_password");
  const pwLabel = document.getElementById("u_password_label");
  const send = document.getElementById("u_send_credentials")?.checked;
  const editId = document.getElementById("u_edit_id")?.value;
  if (!pwInput || !pwLabel) return;
  if (editId) {
    pwInput.required = false;
    pwLabel.textContent = "Nova password (opcional)";
    return;
  }
  if (send) {
    pwInput.required = false;
    pwLabel.textContent = "Password (opcional — gerada se vazio)";
  } else {
    pwInput.required = true;
    pwLabel.textContent = "Password";
  }
}

document.getElementById("u_send_credentials")?.addEventListener("change", syncPasswordOptional);

document.getElementById("btn-new-user")?.addEventListener("click", () => openUserModal(null));

document.getElementById("btn-edit-user-perms")?.addEventListener("click", () => {
  const roleId = Number(document.getElementById("btn-edit-user-perms").dataset.roleId || 0);
  const role = rolesCache.find((r) => r.id === roleId);
  if (!role) return toast("Perfil nao encontrado.", "error");
  closeModal(document.getElementById("modal-user"));
  openRoleEditor(role);
});

document.getElementById("u_role_id")?.addEventListener("change", () => {
  const editId = document.getElementById("u_edit_id").value;
  if (!editId) return;
  const role = rolesCache.find((r) => r.id === Number(document.getElementById("u_role_id").value));
  const permsBtn = document.getElementById("btn-edit-user-perms");
  const permHint = document.getElementById("user-perm-hint");
  const count = role?.permission_codes?.length || 0;
  if (role) {
    permHint.hidden = false;
    permHint.textContent = `Perfil «${role.name}» — ${count} permissao(oes). As permissoes sao do perfil, nao do utilizador individual.`;
    permsBtn.hidden = !canManageRoles();
    permsBtn.dataset.roleId = String(role.id);
  }
});

async function loadRolesSelect() {
  const { roles } = await api("/roles");
  rolesCache = roles || [];
  roleSelect.innerHTML = rolesCache
    .map((r) => `<option value="${r.id}">${escapeHtml(r.name)}</option>`)
    .join("");
  reEnhance(roleSelect);
}

async function loadUsers() {
  setLoading(usersList, "A carregar utilizadores...");
  try {
    const { users } = await api("/users");
    usersCache = users || [];
    renderUsers();
  } catch (err) {
    toast(err.message || "Erro", "error");
    usersList.innerHTML = `<div class="no-data compact"><p>${escapeHtml(err.message)}</p></div>`;
  }
}

function renderUsers() {
  const filtered = filterByQuery(usersCache, usersPager.query, (u) => [
    u.name,
    u.email,
    u.perfil_nome,
    u.role,
    u.status,
  ]);
  const page = paginate(filtered, usersPager.page, usersPager.pageSize);
  usersPager.setMeta(page);
  if (!page.total) {
    usersList.innerHTML = `<div class="no-data compact"><p>Sem utilizadores.</p></div>`;
    return;
  }
  usersList.innerHTML = `
    <table class="data-table">
      <thead><tr><th>Nome</th><th>Email</th><th>Perfil</th><th>Estado</th><th></th></tr></thead>
      <tbody>
        ${page.items
          .map(
            (u) => `
          <tr>
            <td><strong>${escapeHtml(u.name)}</strong></td>
            <td>${escapeHtml(u.email)}</td>
            <td>
              <select class="role-select" data-id="${u.id}">
                ${rolesCache
                  .map(
                    (r) =>
                      `<option value="${r.id}" ${u.role_id === r.id || (!u.role_id && r.slug === u.role) ? "selected" : ""}>${escapeHtml(r.name)}</option>`
                  )
                  .join("")}
              </select>
            </td>
            <td>
              <select class="status-select" data-id="${u.id}">
                <option value="active" ${u.status === "active" ? "selected" : ""}>active</option>
                <option value="inactive" ${u.status === "inactive" ? "selected" : ""}>inactive</option>
              </select>
            </td>
            <td>
              <div class="row-actions">
                ${
                  canManageUsers()
                    ? `<button type="button" class="icon-btn compact" data-edit-user="${u.id}" title="Editar utilizador" aria-label="Editar utilizador"><i class="bi bi-pencil"></i></button>
                       <button type="button" class="icon-btn compact" data-send-creds="${u.id}" title="Redefinir e enviar credenciais" aria-label="Enviar credenciais"><i class="bi bi-envelope-at"></i></button>`
                    : ""
                }
                ${
                  canManageRoles()
                    ? `<button type="button" class="icon-btn compact" data-edit-user-perms="${u.id}" title="Editar permissoes do perfil" aria-label="Editar permissoes"><i class="bi bi-shield-lock"></i></button>`
                    : ""
                }
              </div>
            </td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>`;

  usersList.querySelectorAll(".role-select, .status-select").forEach((sel) => enhanceSelect(sel));
  usersList.querySelectorAll(".role-select").forEach((sel) => {
    sel.addEventListener("change", async () => {
      try {
        await api(`/users/${sel.dataset.id}`, {
          method: "PATCH",
          body: JSON.stringify({ role_id: Number(sel.value) }),
        });
        toast("Perfil actualizado.", "success");
        const row = usersCache.find((x) => x.id === Number(sel.dataset.id));
        if (row) {
          row.role_id = Number(sel.value);
          const role = rolesCache.find((r) => r.id === Number(sel.value));
          if (role) {
            row.perfil_nome = role.name;
            row.role = role.slug;
          }
        }
      } catch (err) {
        toast(err.message || "Erro", "error");
        loadUsers();
      }
    });
  });
  usersList.querySelectorAll(".status-select").forEach((sel) => {
    sel.addEventListener("change", async () => {
      try {
        await api(`/users/${sel.dataset.id}`, {
          method: "PATCH",
          body: JSON.stringify({ status: sel.value }),
        });
        toast("Status actualizado.", "success");
        const row = usersCache.find((x) => x.id === Number(sel.dataset.id));
        if (row) row.status = sel.value;
      } catch (err) {
        toast(err.message || "Erro", "error");
      }
    });
  });
  usersList.querySelectorAll("[data-edit-user]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const u = usersCache.find((x) => x.id === Number(btn.dataset.editUser));
      if (u) openUserModal(u);
    });
  });
  usersList.querySelectorAll("[data-send-creds]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const u = usersCache.find((x) => x.id === Number(btn.dataset.sendCreds));
      if (!u) return;
      if (
        !window.confirm(
          `Redefinir a palavra-passe de «${u.name}» e enviar as novas credenciais por email?`
        )
      ) {
        return;
      }
      btn.disabled = true;
      try {
        const res = await api(`/users/${u.id}/send-credentials`, {
          method: "POST",
          body: "{}",
        });
        toast(
          res.credentials_email_sent
            ? "Credenciais redefinidas e enviadas por email."
            : "Credenciais redefinidas (email nao enviado — verifique Resend).",
          res.credentials_email_sent ? "success" : "error"
        );
      } catch (err) {
        toast(err.message || "Erro ao enviar credenciais", "error");
      } finally {
        btn.disabled = false;
      }
    });
  });
  usersList.querySelectorAll("[data-edit-user-perms]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const u = usersCache.find((x) => x.id === Number(btn.dataset.editUserPerms));
      if (!u) return;
      const role =
        rolesCache.find((r) => r.id === u.role_id) ||
        rolesCache.find((r) => r.slug === u.role);
      if (!role) return toast("Perfil do utilizador nao encontrado.", "error");
      openRoleEditor(role);
    });
  });
}

userForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const editId = document.getElementById("u_edit_id").value;
  const name = document.getElementById("u_name").value.trim();
  const roleId = Number(document.getElementById("u_role_id").value);
  const password = document.getElementById("u_password").value;
  const sendCredentials = document.getElementById("u_send_credentials").checked;
  try {
    if (editId) {
      const body = {
        name,
        role_id: roleId,
        status: document.getElementById("u_status").value,
      };
      if (password) {
        if (password.length < 8) {
          return toast("Password deve ter pelo menos 8 caracteres.", "error");
        }
        body.password = password;
        body.send_credentials = sendCredentials;
      }
      const res = await api(`/users/${editId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      toast(
        password && res.credentials_email_sent
          ? "Utilizador actualizado. Credenciais enviadas."
          : "Utilizador actualizado.",
        "success"
      );
    } else {
      if (!sendCredentials && (!password || password.length < 8)) {
        return toast("Password obrigatoria (min. 8) ou active o envio de credenciais.", "error");
      }
      if (password && password.length < 8) {
        return toast("Password deve ter pelo menos 8 caracteres.", "error");
      }
      const body = {
        name,
        email: document.getElementById("u_email").value,
        role_id: roleId,
        send_credentials: sendCredentials,
      };
      if (password) body.password = password;
      const res = await api("/users", {
        method: "POST",
        body: JSON.stringify(body),
      });
      toast(
        sendCredentials && res.credentials_email_sent
          ? "Utilizador criado. Credenciais enviadas por email."
          : sendCredentials
            ? "Utilizador criado (email nao enviado — verifique Resend)."
            : "Utilizador criado.",
        "success"
      );
    }
    closeModal(document.getElementById("modal-user"));
    loadUsers();
    await loadRoles();
  } catch (err) {
    toast(err.message || "Falha ao guardar", "error");
  }
});

/* ── Roles ── */
function renderPermEditor(selected = []) {
  const el = document.getElementById("perm-editor");
  const groups = {};
  permissionsCache.forEach((p) => {
    groups[p.group_name] = groups[p.group_name] || [];
    groups[p.group_name].push(p);
  });
  el.innerHTML = Object.entries(groups)
    .map(
      ([g, items]) => `
      <div class="perm-group">
        <h5>${escapeHtml(g)}</h5>
        <div class="perm-grid">
          ${items
            .map(
              (p) => `
            <label class="perm-item">
              <input type="checkbox" name="perm" value="${escapeHtml(p.code)}" ${selected.includes(p.code) ? "checked" : ""} />
              <span><strong>${escapeHtml(p.name)}</strong><br/><small>${escapeHtml(p.code)}</small></span>
            </label>`
            )
            .join("")}
        </div>
      </div>`
    )
    .join("");
}

function selectedPerms() {
  return [...document.querySelectorAll('#perm-editor input[name="perm"]:checked')].map((i) => i.value);
}

document.getElementById("btn-new-role")?.addEventListener("click", () => {
  roleForm.dataset.editId = "";
  document.getElementById("role-modal-title").textContent = "Novo perfil";
  document.getElementById("r_name").value = "";
  document.getElementById("r_slug").value = "";
  document.getElementById("r_slug").disabled = false;
  document.getElementById("r_desc").value = "";
  renderPermEditor([]);
  openModal(document.getElementById("modal-role"));
});

async function loadPermissions() {
  const { permissions } = await api("/permissions");
  permissionsCache = permissions || [];
}

async function loadRoles() {
  setLoading(rolesList, "A carregar perfis...");
  try {
    const { roles } = await api("/roles");
    rolesCache = roles || [];
    renderRoles();
  } catch (err) {
    rolesList.innerHTML = `<div class="no-data compact"><p>${escapeHtml(err.message)}</p></div>`;
  }
}

function renderRoles() {
  const filtered = filterByQuery(rolesCache, rolesPager.query, (r) => [
    r.name,
    r.slug,
    r.description,
    r.is_system ? "sistema" : "custom",
    ...(r.permission_codes || []),
  ]);
  const page = paginate(filtered, rolesPager.page, rolesPager.pageSize);
  rolesPager.setMeta(page);
  if (!page.total) {
    rolesList.innerHTML = `<div class="no-data compact"><p>Sem perfis.</p></div>`;
    return;
  }
  rolesList.innerHTML = `
    <table class="data-table">
      <thead><tr><th>Perfil</th><th>Slug</th><th>Permissoes</th><th></th></tr></thead>
      <tbody>
        ${page.items
          .map(
            (r) => `
          <tr>
            <td><strong>${escapeHtml(r.name)}</strong> ${r.is_system ? `<span class="status-pill neutro">sistema</span>` : ""}</td>
            <td>${escapeHtml(r.slug)}</td>
            <td>${r.permission_codes?.length || 0}</td>
            <td>
              <div class="row-actions">
                <button type="button" class="icon-btn compact" data-role-id="${r.id}" title="Editar perfil e permissoes" aria-label="Editar"><i class="bi bi-pencil"></i></button>
              </div>
            </td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>`;
  rolesList.querySelectorAll("[data-role-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const role = rolesCache.find((x) => x.id === Number(btn.dataset.roleId));
      openRoleEditor(role);
    });
  });
}

roleForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const editId = roleForm.dataset.editId;
  const payload = {
    name: document.getElementById("r_name").value,
    description: document.getElementById("r_desc").value,
    permission_codes: selectedPerms(),
  };
  try {
    if (editId) {
      await api(`/roles/${editId}`, { method: "PATCH", body: JSON.stringify(payload) });
      toast("Perfil actualizado.", "success");
    } else {
      await api("/roles", {
        method: "POST",
        body: JSON.stringify({ ...payload, slug: document.getElementById("r_slug").value }),
      });
      toast("Perfil criado.", "success");
    }
    closeModal(document.getElementById("modal-role"));
    await loadRoles();
    await loadRolesSelect();
  } catch (err) {
    toast(err.message || "Erro", "error");
  }
});

async function loadPilares() {
  setLoading(adminPilares);
  try {
    const { pilares } = await api("/admin/pilares");
    pilaresCache = pilares || [];
    renderPilares();
  } catch (err) {
    adminPilares.innerHTML = `<div class="no-data compact"><p>${escapeHtml(err.message)}</p></div>`;
  }
}

document.getElementById("btn-export-pilares")?.addEventListener("click", async () => {
  try {
    await apiDownload("/pilares/export.xlsx", "projectos-export.xlsx");
    toast("Exportacao iniciada.", "success");
  } catch (err) {
    toast(err.message || "Erro ao exportar", "error");
  }
});

document.getElementById("btn-template-pilares")?.addEventListener("click", async () => {
  try {
    await apiDownload("/pilares/import-template.xlsx", "projectos-modelo.xlsx");
    toast("Modelo descarregado.", "success");
  } catch (err) {
    toast(err.message || "Erro", "error");
  }
});

document.getElementById("import-pilares-file")?.addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (!file) return;
  await runProjectImport(file, { onSuccess: () => loadPilares() });
});

function renderPilares() {
  const filtered = filterByQuery(pilaresCache, pilaresPager.query, (p) => [
    p.nome,
    p.area,
    p.fase,
    p.status,
    p.proxima_avaliacao,
  ]);
  const page = paginate(filtered, pilaresPager.page, pilaresPager.pageSize);
  pilaresPager.setMeta(page);
  if (!page.total) {
    adminPilares.innerHTML = `<div class="no-data compact"><p>Sem projectos. Crie o primeiro.</p></div>`;
    return;
  }
  adminPilares.innerHTML = `
    <table class="data-table">
      <thead><tr><th>Projecto</th><th>Area</th><th>Fase</th><th>Status</th><th>Prox. avaliacao</th><th></th></tr></thead>
      <tbody>
        ${page.items
          .map(
            (p) => `
          <tr>
            <td><strong>${escapeHtml(p.nome)}</strong></td>
            <td>${escapeHtml(p.area || "—")}</td>
            <td>${escapeHtml(p.fase || "—")}</td>
            <td><span class="status-pill ${
              p.status === "activo" ? "ok" : p.status === "concluido" ? "ok" : "neutro"
            }">${escapeHtml(p.status)}</span></td>
            <td>${escapeHtml(p.proxima_avaliacao || "—")}</td>
            <td>
              <div class="row-actions">
                <a class="icon-btn compact" href="/admin/projectos/${p.id}" title="Editar" aria-label="Editar"><i class="bi bi-pencil"></i></a>
              </div>
            </td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>`;
}

/* ── Catalog ── */
async function loadCatalog() {
  catalogData = await api("/catalog");
  renderCatalog();
}

function renderCatalog() {
  const root = document.getElementById("catalog-root");
  const cats = catalogData.categories || {};
  const allowManage = canCatalog();
  root.innerHTML = Object.entries(cats)
    .map(([key, label]) => {
      const opts = catalogData.options?.[key] || [];
      return `
        <div class="nested-block" style="margin-bottom:14px">
          <div class="panel-head" style="margin-bottom:8px">
            <h4 style="margin:0">${escapeHtml(label)}</h4>
            ${
              allowManage
                ? `<button type="button" class="btn btn-outline compact" data-add-cat="${escapeHtml(key)}"><i class="bi bi-plus-lg"></i> Opcao</button>`
                : ""
            }
          </div>
          <table class="data-table">
            <thead><tr><th>Codigo</th><th>Etiqueta</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              ${
                opts
                  .map(
                    (o) => `
                <tr>
                  <td><code>${escapeHtml(o.code)}</code></td>
                  <td>${escapeHtml(o.label)}</td>
                  <td>${o.active ? `<span class="status-pill ok">activo</span>` : `<span class="status-pill neutro">inactivo</span>`}${o.in_use ? ` <span class="status-pill neutro">em uso</span>` : ""}</td>
                  <td>
                    <div class="row-actions">
                      ${
                        allowManage
                          ? `
                      <button type="button" class="icon-btn compact" data-edit-cat="${o.id}" title="Editar" aria-label="Editar"><i class="bi bi-pencil"></i></button>
                      <button type="button" class="icon-btn compact" data-toggle-cat="${o.id}" data-active="${o.active ? "0" : "1"}" title="${o.active ? "Desactivar" : "Activar"}" aria-label="${o.active ? "Desactivar" : "Activar"}">
                        <i class="bi ${o.active ? "bi-pause-circle" : "bi-play-circle"}"></i>
                      </button>
                      <button type="button" class="icon-btn compact danger" data-del-cat="${o.id}" ${o.in_use ? "disabled title='Associado a projectos'" : 'title="Remover"'} aria-label="Remover"><i class="bi bi-trash"></i></button>`
                          : "—"
                      }
                    </div>
                  </td>
                </tr>`
                  )
                  .join("") || `<tr><td colspan="4">Sem opcoes</td></tr>`
              }
            </tbody>
          </table>
        </div>`;
    })
    .join("");

  root.querySelectorAll("[data-add-cat]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById("cat_edit_id").value = "";
      document.getElementById("cat_category").value = btn.dataset.addCat;
      document.getElementById("catalog-item-title").textContent = `Nova opcao — ${cats[btn.dataset.addCat] || ""}`;
      document.getElementById("cat_code").value = "";
      document.getElementById("cat_code").disabled = false;
      document.getElementById("cat_label").value = "";
      openModal(document.getElementById("modal-catalog-item"));
    });
  });
  root.querySelectorAll("[data-edit-cat]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = Number(btn.dataset.editCat);
      let found = null;
      let catKey = "";
      for (const [key, list] of Object.entries(catalogData.options || {})) {
        const hit = (list || []).find((o) => o.id === id);
        if (hit) {
          found = hit;
          catKey = key;
          break;
        }
      }
      if (!found) return;
      document.getElementById("cat_edit_id").value = String(found.id);
      document.getElementById("cat_category").value = catKey;
      document.getElementById("catalog-item-title").textContent = `Editar opcao — ${cats[catKey] || ""}`;
      document.getElementById("cat_code").value = found.code;
      document.getElementById("cat_code").disabled = true;
      document.getElementById("cat_label").value = found.label;
      openModal(document.getElementById("modal-catalog-item"));
    });
  });
  root.querySelectorAll("[data-del-cat]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await api(`/catalog/item/${btn.dataset.delCat}`, { method: "DELETE" });
        toast("Opcao removida.", "success");
        loadCatalog();
      } catch (err) {
        toast(err.message || "Erro", "error");
      }
    });
  });
  root.querySelectorAll("[data-toggle-cat]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await api(`/catalog/item/${btn.dataset.toggleCat}`, {
          method: "PATCH",
          body: JSON.stringify({ active: btn.dataset.active === "1" }),
        });
        loadCatalog();
      } catch (err) {
        toast(err.message || "Erro", "error");
      }
    });
  });
}

document.getElementById("btn-confirm-catalog")?.addEventListener("click", async () => {
  const editId = document.getElementById("cat_edit_id").value;
  const label = document.getElementById("cat_label").value.trim();
  if (!label) return toast("Indique a etiqueta.", "error");
  try {
    if (editId) {
      await api(`/catalog/item/${editId}`, {
        method: "PATCH",
        body: JSON.stringify({ label }),
      });
      toast("Opcao actualizada.", "success");
    } else {
      await api("/catalog", {
        method: "POST",
        body: JSON.stringify({
          category: document.getElementById("cat_category").value,
          code: document.getElementById("cat_code").value.trim(),
          label,
        }),
      });
      toast("Opcao criada.", "success");
    }
    closeModal(document.getElementById("modal-catalog-item"));
    loadCatalog();
  } catch (err) {
    toast(err.message || "Erro", "error");
  }
});

try {
  await loadPermissions();
  await loadCatalog();
  await loadRolesSelect();
  await loadUsers();
  await loadRoles();
  await loadPilares();
} catch (err) {
  toast(err.message || "Falha ao carregar admin", "error");
}
