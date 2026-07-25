/** Pagina dedicada — criar / editar projecto. */
import { api } from "../api.js";
import { addDaysISO, bindDatePicker } from "../components/dates.js";
import { bindModalDismiss, closeModal, openModal } from "../components/modal.js";
import { enhanceSelect } from "../components/styled-select.js";
import { bootPage } from "../shell.js";
import { toast } from "../ui.js";

const LIST_URL = "/admin#projectos";

function parseRoute() {
  const parts = location.pathname.replace(/\/+$/, "").split("/").filter(Boolean);
  const last = parts[parts.length - 1] || "";
  if (last === "novo") return { id: null };
  if (/^\d+$/.test(last)) return { id: last };
  const q = new URLSearchParams(location.search).get("id");
  return { id: q && /^\d+$/.test(q) ? q : null };
}

const route = parseRoute();

const { user } = await bootPage({
  page: "admin",
  title: route.id ? "Editar projecto" : "Novo projecto",
  subtitle: "Dados mestre do projecto",
});

const perms = new Set(user?.permissions || []);
const isAdmin = user?.role === "admin";
const can = (code) => isAdmin || perms.has(code) || perms.has("projectos.manage");
const canManage = () => isAdmin || perms.has("projectos.manage");
const canDeactivate = () => can("projectos.deactivate");
const canDelete = () => can("projectos.delete");

if (!canManage() && !route.id) {
  toast("Sem permissao para criar projectos.", "error");
  window.location.replace(LIST_URL);
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function formatMoney(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? "0");
  return n.toLocaleString("pt-MZ", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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

["modal-act", "modal-orc", "modal-risco"].forEach((id) =>
  bindModalDismiss(document.getElementById(id))
);

let catalogData = { categories: {}, options: {} };
let draft = emptyDraft();
let proxPicker = null;
/** @type {{ kind: 'existing' | 'pending', id?: number, index?: number } | null} */
let editOrc = null;
/** @type {{ kind: 'existing' | 'pending', id?: number, index?: number } | null} */
let editRisco = null;

function emptyDraft(pilar = null) {
  return {
    existingActs: [...(pilar?.actividades || [])],
    existingOrcs: [...(pilar?.orcamento_categorias || [])].map((o) => ({ ...o })),
    existingRiscos: [...(pilar?.riscos || [])].map((r) => ({ ...r })),
    pendingActs: [],
    pendingOrcs: [],
    pendingRiscos: [],
    deleteActs: new Set(),
    deleteOrcs: new Set(),
    deleteRiscos: new Set(),
    dirtyOrcs: new Set(),
    dirtyRiscos: new Set(),
  };
}

function fillCatalogSelect(select, category, preferred) {
  const opts = catalogData.options?.[category] || [];
  select.innerHTML =
    `<option value="">—</option>` +
    opts
      .filter((o) => o.active !== false)
      .map((o) => {
        const selected =
          preferred && (preferred === o.code || preferred === o.label) ? "selected" : "";
        return `<option value="${escapeHtml(o.code)}" ${selected}>${escapeHtml(o.label)}</option>`;
      })
      .join("");
  if (
    preferred &&
    ![...select.options].some((o) => o.value === preferred || o.textContent === preferred)
  ) {
    const opt = document.createElement("option");
    opt.value = preferred;
    opt.textContent = preferred;
    opt.selected = true;
    select.appendChild(opt);
  }
  reEnhance(select);
}

function syncOrcTotal() {
  const total =
    draft.existingOrcs
      .filter((o) => !draft.deleteOrcs.has(o.id))
      .reduce((sum, o) => sum + (Number(o.valor_alocado) || 0), 0) +
    draft.pendingOrcs.reduce((sum, o) => sum + (Number(o.valor_alocado) || 0), 0);
  const el = document.getElementById("p_orc");
  if (el) el.value = total ? total.toFixed(2) : "0.00";
}

function paintChips() {
  const actEl = document.getElementById("p_act_chips");
  const orcEl = document.getElementById("p_orc_list");
  const riscoEl = document.getElementById("p_risco_list");

  actEl.innerHTML = [
    ...draft.existingActs.map((a) => {
      const del = draft.deleteActs.has(a.id);
      return `<span class="chip ${del ? "muted" : ""}" data-kind="act" data-id="${a.id}">
        <span>${escapeHtml(a.nome)}</span>
        <button type="button" title="${del ? "Restaurar" : "Remover"}"><i class="bi ${del ? "bi-arrow-counterclockwise" : "bi-x"}"></i></button>
      </span>`;
    }),
    ...draft.pendingActs.map(
      (a, i) => `<span class="chip" data-kind="act-new" data-i="${i}">
        <span>+ ${escapeHtml(a.nome)}</span>
        <button type="button"><i class="bi bi-x"></i></button>
      </span>`
    ),
  ].join("") || `<p class="empty-chips">Nenhuma actividade ainda.</p>`;

  const orcRows = [
    ...draft.existingOrcs.map((o) => {
      const del = draft.deleteOrcs.has(o.id);
      return `<li class="nested-item ${del ? "is-removed" : ""}" data-kind="orc" data-id="${o.id}">
        <div class="nested-item-body">
          <strong>${escapeHtml(o.categoria)}</strong>
          <span class="nested-item-meta">${formatMoney(o.valor_alocado)}</span>
        </div>
        <div class="nested-item-actions">
          ${
            del
              ? ""
              : `<button type="button" class="nested-item-btn" data-action="edit" title="Editar"><i class="bi bi-pencil"></i></button>`
          }
          <button type="button" class="nested-item-btn" data-action="toggle" title="${del ? "Restaurar" : "Remover"}">
            <i class="bi ${del ? "bi-arrow-counterclockwise" : "bi-trash"}"></i>
          </button>
        </div>
      </li>`;
    }),
    ...draft.pendingOrcs.map(
      (o, i) => `<li class="nested-item is-new" data-kind="orc-new" data-i="${i}">
        <div class="nested-item-body">
          <strong>${escapeHtml(o.categoria)}</strong>
          <span class="nested-item-meta">${formatMoney(o.valor_alocado)}</span>
        </div>
        <div class="nested-item-actions">
          <button type="button" class="nested-item-btn" data-action="edit" title="Editar"><i class="bi bi-pencil"></i></button>
          <button type="button" class="nested-item-btn" data-action="remove" title="Remover"><i class="bi bi-trash"></i></button>
        </div>
      </li>`
    ),
  ];
  orcEl.innerHTML = orcRows.length
    ? `<ul class="nested-item-list">${orcRows.join("")}</ul>`
    : `<p class="empty-chips">Nenhuma rubrica ainda.</p>`;

  const riscoRows = [
    ...draft.existingRiscos.map((r) => {
      const del = draft.deleteRiscos.has(r.id);
      return `<li class="nested-item ${del ? "is-removed" : ""}" data-kind="risco" data-id="${r.id}">
        <div class="nested-item-body">
          <strong>${escapeHtml(r.descricao)}</strong>
          <span class="nested-item-meta">${escapeHtml(r.probabilidade)} / ${escapeHtml(r.impacto)}${
            r.mitigacao ? ` · ${escapeHtml(r.mitigacao)}` : ""
          }</span>
        </div>
        <div class="nested-item-actions">
          ${
            del
              ? ""
              : `<button type="button" class="nested-item-btn" data-action="edit" title="Editar"><i class="bi bi-pencil"></i></button>`
          }
          <button type="button" class="nested-item-btn" data-action="toggle" title="${del ? "Restaurar" : "Remover"}">
            <i class="bi ${del ? "bi-arrow-counterclockwise" : "bi-trash"}"></i>
          </button>
        </div>
      </li>`;
    }),
    ...draft.pendingRiscos.map(
      (r, i) => `<li class="nested-item is-new" data-kind="risco-new" data-i="${i}">
        <div class="nested-item-body">
          <strong>${escapeHtml(r.descricao)}</strong>
          <span class="nested-item-meta">${escapeHtml(r.probabilidade)} / ${escapeHtml(r.impacto)}${
            r.mitigacao ? ` · ${escapeHtml(r.mitigacao)}` : ""
          }</span>
        </div>
        <div class="nested-item-actions">
          <button type="button" class="nested-item-btn" data-action="edit" title="Editar"><i class="bi bi-pencil"></i></button>
          <button type="button" class="nested-item-btn" data-action="remove" title="Remover"><i class="bi bi-trash"></i></button>
        </div>
      </li>`
    ),
  ];
  riscoEl.innerHTML = riscoRows.length
    ? `<ul class="nested-item-list">${riscoRows.join("")}</ul>`
    : `<p class="empty-chips">Nenhum risco ainda.</p>`;

  syncOrcTotal();
}

function bindActChipClicks() {
  document.getElementById("p_act_chips")?.addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    const chip = e.target.closest(".chip");
    if (!btn || !chip) return;
    const kind = chip.dataset.kind;
    if (kind === "act") {
      const id = Number(chip.dataset.id);
      if (draft.deleteActs.has(id)) draft.deleteActs.delete(id);
      else draft.deleteActs.add(id);
    } else if (kind === "act-new") draft.pendingActs.splice(Number(chip.dataset.i), 1);
    paintChips();
  });
}
bindActChipClicks();

function openOrcModal(mode) {
  editOrc = mode;
  const isEdit = Boolean(mode);
  document.getElementById("modal-orc-title").textContent = isEdit ? "Editar rubrica" : "Nova rubrica";
  document.getElementById("btn-confirm-orc").textContent = isEdit ? "Guardar" : "Adicionar";
  openModal(document.getElementById("modal-orc"));
}

function openRiscoModal(mode) {
  editRisco = mode;
  const isEdit = Boolean(mode);
  document.getElementById("modal-risco-title").textContent = isEdit ? "Editar risco" : "Novo risco";
  document.getElementById("btn-confirm-risco").textContent = isEdit ? "Guardar" : "Adicionar";
  openModal(document.getElementById("modal-risco"));
}

function bindNestedList(rootId) {
  document.getElementById(rootId)?.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    const row = e.target.closest(".nested-item");
    if (!btn || !row) return;
    const action = btn.dataset.action;
    const kind = row.dataset.kind;

    if (kind === "orc" || kind === "orc-new") {
      if (action === "edit") {
        if (kind === "orc") {
          const id = Number(row.dataset.id);
          const item = draft.existingOrcs.find((o) => o.id === id);
          if (!item || draft.deleteOrcs.has(id)) return;
          document.getElementById("orc_cat").value = item.categoria || "";
          document.getElementById("orc_val").value = item.valor_alocado ?? "0";
          openOrcModal({ kind: "existing", id });
        } else {
          const index = Number(row.dataset.i);
          const item = draft.pendingOrcs[index];
          if (!item) return;
          document.getElementById("orc_cat").value = item.categoria || "";
          document.getElementById("orc_val").value = item.valor_alocado ?? "0";
          openOrcModal({ kind: "pending", index });
        }
        return;
      }
      if (action === "toggle" && kind === "orc") {
        const id = Number(row.dataset.id);
        if (draft.deleteOrcs.has(id)) draft.deleteOrcs.delete(id);
        else draft.deleteOrcs.add(id);
      } else if (action === "remove" && kind === "orc-new") {
        draft.pendingOrcs.splice(Number(row.dataset.i), 1);
      }
      paintChips();
      return;
    }

    if (kind === "risco" || kind === "risco-new") {
      if (action === "edit") {
        if (kind === "risco") {
          const id = Number(row.dataset.id);
          const item = draft.existingRiscos.find((r) => r.id === id);
          if (!item || draft.deleteRiscos.has(id)) return;
          document.getElementById("risco_desc").value = item.descricao || "";
          document.getElementById("risco_nivel").value = item.probabilidade || "media";
          document.getElementById("risco_impacto").value = item.impacto || "medio";
          document.getElementById("risco_mit").value = item.mitigacao || "";
          reEnhance(document.getElementById("risco_nivel"));
          reEnhance(document.getElementById("risco_impacto"));
          openRiscoModal({ kind: "existing", id });
        } else {
          const index = Number(row.dataset.i);
          const item = draft.pendingRiscos[index];
          if (!item) return;
          document.getElementById("risco_desc").value = item.descricao || "";
          document.getElementById("risco_nivel").value = item.probabilidade || "media";
          document.getElementById("risco_impacto").value = item.impacto || "medio";
          document.getElementById("risco_mit").value = item.mitigacao || "";
          reEnhance(document.getElementById("risco_nivel"));
          reEnhance(document.getElementById("risco_impacto"));
          openRiscoModal({ kind: "pending", index });
        }
        return;
      }
      if (action === "toggle" && kind === "risco") {
        const id = Number(row.dataset.id);
        if (draft.deleteRiscos.has(id)) draft.deleteRiscos.delete(id);
        else draft.deleteRiscos.add(id);
      } else if (action === "remove" && kind === "risco-new") {
        draft.pendingRiscos.splice(Number(row.dataset.i), 1);
      }
      paintChips();
    }
  });
}
bindNestedList("p_orc_list");
bindNestedList("p_risco_list");

function syncProximaFromPeriod() {
  const days = Number(document.getElementById("p_period").value || 90);
  const iso = addDaysISO(days);
  document.getElementById("p_prox").value = iso;
  if (proxPicker) proxPicker.setDate(iso, true);
}

function fillForm(pilar) {
  draft = emptyDraft(pilar);
  editOrc = null;
  editRisco = null;
  document.getElementById("p_edit_id").value = pilar?.id || "";
  document.getElementById("pilar-page-title").textContent = pilar?.id
    ? "Editar projecto"
    : "Novo projecto";
  document.title = pilar?.id ? `Editar — ${pilar.nome || "Projecto"}` : "Novo projecto";
  document.getElementById("btn-save-pilar").textContent = pilar?.id ? "Actualizar" : "Guardar projecto";
  document.getElementById("p_nome").value = pilar?.nome || "";
  document.getElementById("p_status").value = pilar?.status || "activo";
  document.getElementById("p_period").value = pilar?.periodicidade_dias ?? 90;
  document.getElementById("p_desc").value = pilar?.descricao || "";
  document.getElementById("p_obj").value = pilar?.obj_geral || "";
  document.getElementById("p_kpis").value = pilar?.kpis || "";
  document.getElementById("p_benef").value = pilar?.beneficios || "";

  fillCatalogSelect(document.getElementById("p_area"), "area", pilar?.area || "");
  fillCatalogSelect(document.getElementById("p_fase"), "fase", pilar?.fase || "");
  fillCatalogSelect(document.getElementById("p_moeda"), "moeda", pilar?.orc_moeda || "MZN");
  fillCatalogSelect(document.getElementById("p_fonte"), "fonte_financiamento", pilar?.orc_fonte || "");
  reEnhance(document.getElementById("p_status"));

  const prox = pilar?.proxima_avaliacao || addDaysISO(pilar?.periodicidade_dias ?? 90);
  document.getElementById("p_prox").value = prox;
  proxPicker = bindDatePicker(document.getElementById("p_prox"), { defaultDate: prox });

  document.getElementById("pilar-hint").textContent = pilar?.id
    ? "Alteracoes so sao gravadas ao clicar Actualizar. Remocoes de rubricas com execucao serao rejeitadas."
    : "A proxima avaliacao e calculada como hoje + periodicidade (pode ajustar).";

  const danger = document.getElementById("pilar-danger-actions");
  if (danger) {
    danger.hidden = !pilar?.id;
    const deactBtn = document.getElementById("btn-deactivate-pilar");
    const delBtn = document.getElementById("btn-delete-pilar");
    if (deactBtn) {
      deactBtn.hidden = !canDeactivate();
      const inactive = pilar?.status === "inactivo";
      deactBtn.innerHTML = inactive
        ? `<i class="bi bi-play-circle"></i> Activar`
        : `<i class="bi bi-pause-circle"></i> Desactivar`;
      deactBtn.dataset.nextStatus = inactive ? "activo" : "inactivo";
    }
    if (delBtn) delBtn.hidden = !canDelete();
  }

  paintChips();
}

document.getElementById("p_period")?.addEventListener("change", syncProximaFromPeriod);

document.getElementById("btn-deactivate-pilar")?.addEventListener("click", async () => {
  const editId = document.getElementById("p_edit_id").value;
  if (!editId || !canDeactivate()) return;
  const next = document.getElementById("btn-deactivate-pilar").dataset.nextStatus || "inactivo";
  const label = next === "inactivo" ? "desactivar" : "activar";
  if (!confirm(`Tem a certeza que pretende ${label} este projecto?`)) return;
  try {
    await api(`/pilares/${editId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: next }),
    });
    toast(next === "inactivo" ? "Projecto desactivado." : "Projecto activado.", "success");
    window.location.href = LIST_URL;
  } catch (err) {
    toast(err.message || "Erro", "error");
  }
});

document.getElementById("btn-delete-pilar")?.addEventListener("click", async () => {
  const editId = document.getElementById("p_edit_id").value;
  if (!editId || !canDelete()) return;
  if (
    !confirm(
      "Apagar permanentemente este projecto? So e permitido se nao tiver avaliacoes. Esta accao nao pode ser anulada."
    )
  ) {
    return;
  }
  try {
    await api(`/pilares/${editId}`, { method: "DELETE" });
    toast("Projecto apagado.", "success");
    window.location.href = LIST_URL;
  } catch (err) {
    toast(err.message || "Erro ao apagar", "error");
  }
});

document.getElementById("btn-add-act")?.addEventListener("click", () => {
  document.getElementById("act_nome").value = "";
  document.getElementById("act_resp").value = "";
  document.getElementById("act_prio").value = "media";
  reEnhance(document.getElementById("act_prio"));
  openModal(document.getElementById("modal-act"));
});
document.getElementById("btn-confirm-act")?.addEventListener("click", () => {
  const nome = document.getElementById("act_nome").value.trim();
  if (!nome) return toast("Indique o nome da actividade.", "error");
  draft.pendingActs.push({
    nome,
    responsavel: document.getElementById("act_resp").value.trim(),
    prioridade: document.getElementById("act_prio").value,
  });
  closeModal(document.getElementById("modal-act"));
  paintChips();
});

document.getElementById("btn-add-orc")?.addEventListener("click", () => {
  document.getElementById("orc_cat").value = "";
  document.getElementById("orc_val").value = "0";
  openOrcModal(null);
});
document.getElementById("btn-confirm-orc")?.addEventListener("click", () => {
  const categoria = document.getElementById("orc_cat").value.trim();
  if (!categoria) return toast("Indique a categoria.", "error");
  const valor_alocado = document.getElementById("orc_val").value || "0";
  if (editOrc?.kind === "existing") {
    const item = draft.existingOrcs.find((o) => o.id === editOrc.id);
    if (item) {
      item.categoria = categoria;
      item.valor_alocado = valor_alocado;
      draft.dirtyOrcs.add(item.id);
    }
  } else if (editOrc?.kind === "pending") {
    const item = draft.pendingOrcs[editOrc.index];
    if (item) {
      item.categoria = categoria;
      item.valor_alocado = valor_alocado;
    }
  } else {
    draft.pendingOrcs.push({ categoria, valor_alocado });
  }
  editOrc = null;
  closeModal(document.getElementById("modal-orc"));
  paintChips();
});

document.getElementById("btn-add-risco")?.addEventListener("click", () => {
  document.getElementById("risco_desc").value = "";
  document.getElementById("risco_nivel").value = "media";
  document.getElementById("risco_impacto").value = "medio";
  document.getElementById("risco_mit").value = "";
  reEnhance(document.getElementById("risco_nivel"));
  reEnhance(document.getElementById("risco_impacto"));
  openRiscoModal(null);
});
document.getElementById("btn-confirm-risco")?.addEventListener("click", () => {
  const descricao = document.getElementById("risco_desc").value.trim();
  if (!descricao) return toast("Descreva o risco.", "error");
  const payload = {
    descricao,
    probabilidade: document.getElementById("risco_nivel").value,
    impacto: document.getElementById("risco_impacto").value,
    mitigacao: document.getElementById("risco_mit").value.trim() || null,
  };
  if (editRisco?.kind === "existing") {
    const item = draft.existingRiscos.find((r) => r.id === editRisco.id);
    if (item) {
      Object.assign(item, payload);
      draft.dirtyRiscos.add(item.id);
    }
  } else if (editRisco?.kind === "pending") {
    const item = draft.pendingRiscos[editRisco.index];
    if (item) Object.assign(item, payload);
  } else {
    draft.pendingRiscos.push(payload);
  }
  editRisco = null;
  closeModal(document.getElementById("modal-risco"));
  paintChips();
});

document.getElementById("pilar-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!canManage()) {
    toast("Sem permissao para guardar.", "error");
    return;
  }
  const editId = document.getElementById("p_edit_id").value;
  syncOrcTotal();
  const base = {
    nome: document.getElementById("p_nome").value.trim(),
    area: document.getElementById("p_area").value,
    fase: document.getElementById("p_fase").value,
    status: document.getElementById("p_status").value,
    orc_aprovado: document.getElementById("p_orc").value || "0",
    orc_moeda: document.getElementById("p_moeda").value || "MZN",
    orc_fonte: document.getElementById("p_fonte").value || null,
    periodicidade_dias: Number(document.getElementById("p_period").value || 90),
    proxima_avaliacao: document.getElementById("p_prox").value || null,
    descricao: document.getElementById("p_desc").value,
    obj_geral: document.getElementById("p_obj").value,
    kpis: document.getElementById("p_kpis").value,
    beneficios: document.getElementById("p_benef").value,
  };
  if (draft.pendingActs.length) base.actividades = draft.pendingActs;

  const orcPayload = [
    ...draft.existingOrcs
      .filter((o) => !draft.deleteOrcs.has(o.id) && draft.dirtyOrcs.has(o.id))
      .map((o) => ({
        id: o.id,
        categoria: o.categoria,
        valor_alocado: o.valor_alocado,
        obs: o.obs ?? null,
      })),
    ...draft.pendingOrcs,
  ];
  if (orcPayload.length) base.orcamento_categorias = orcPayload;

  const riscoPayload = [
    ...draft.existingRiscos
      .filter((r) => !draft.deleteRiscos.has(r.id) && draft.dirtyRiscos.has(r.id))
      .map((r) => ({
        id: r.id,
        descricao: r.descricao,
        probabilidade: r.probabilidade,
        impacto: r.impacto,
        mitigacao: r.mitigacao ?? null,
      })),
    ...draft.pendingRiscos,
  ];
  if (riscoPayload.length) base.riscos = riscoPayload;

  if (editId) {
    base.delete_actividade_ids = [...draft.deleteActs];
    base.delete_categoria_ids = [...draft.deleteOrcs];
    base.delete_risco_ids = [...draft.deleteRiscos];
  }

  const btn = document.getElementById("btn-save-pilar");
  btn.disabled = true;
  try {
    if (editId) {
      await api(`/pilares/${editId}`, { method: "PATCH", body: JSON.stringify(base) });
      toast("Projecto actualizado.", "success");
    } else {
      const { pilar } = await api("/pilares", { method: "POST", body: JSON.stringify(base) });
      toast("Projecto criado.", "success");
      if (pilar?.id) {
        window.location.replace(`/admin/projectos/${pilar.id}`);
        return;
      }
    }
    window.location.href = LIST_URL;
  } catch (err) {
    toast(err.message || "Erro ao guardar", "error");
  } finally {
    btn.disabled = false;
  }
});

try {
  catalogData = await api("/catalog");
  if (route.id) {
    const { pilar } = await api(`/pilares/${route.id}`);
    fillForm(pilar);
  } else {
    fillForm(null);
  }
} catch (err) {
  toast(err.message || "Erro ao carregar", "error");
  if (route.id) window.location.replace(LIST_URL);
}
