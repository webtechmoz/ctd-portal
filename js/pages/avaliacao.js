/** Avaliacao — acompanhamento de execucao com baseline da avaliacao anterior. */
import { api, apiForm, formatBytes } from "../api.js";
import { bindDatePicker, addDaysISO } from "../components/dates.js";
import { mountPilarPicker } from "../components/pilar-picker.js";
import { bootPage } from "../shell.js";
import { toast } from "../ui.js";

await bootPage({
  page: "avaliacoes",
  title: "Nova avaliacao",
  subtitle: "Actualize o progresso do periodo",
});

const pickerHost = document.getElementById("pilar-picker");
const form = document.getElementById("avaliacao-form");
const empty = document.getElementById("aval-empty");

let currentPilar = null;
let previousAval = null;
let picker = null;
/** @type {File[]} */
let pendingAnexos = [];

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function todayISO() {
  return addDaysISO(0);
}

function fmtMoney(n) {
  return Number(n || 0).toLocaleString("pt-MZ", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function enumLabel(v) {
  return String(v ?? "—").replaceAll("_", " ");
}

function estadoFromPct(pct) {
  const n = Number(pct) || 0;
  if (n >= 100) return "concluida";
  if (n > 0) return "em_progresso";
  return "pendente";
}

function estadoBadge(estado) {
  const map = {
    pendente: "neutro",
    em_progresso: "warn",
    concluida: "ok",
  };
  const label =
    estado === "em_progresso" ? "Em progresso" : estado === "concluida" ? "Concluida" : "Pendente";
  return `<span class="status-pill ${map[estado] || "neutro"}">${label}</span>`;
}

function prevAct(actId) {
  return (previousAval?.actividades || []).find((a) => a.pilar_actividade_id === actId) || null;
}

function prevOrc(catId) {
  return (previousAval?.orcamentos || []).find((o) => o.categoria_id === catId) || null;
}

function applyActivityDerived(row) {
  const pctInput = row.querySelector(".exec-pct");
  let pct = Number(pctInput.value);
  if (Number.isNaN(pct)) pct = 0;
  if (pct > 100) {
    pct = 100;
    pctInput.value = "100";
  }

  const estado = estadoFromPct(pct);
  row.dataset.estado = estado;
  const badge = row.querySelector(".exec-estado-badge");
  if (badge) badge.innerHTML = estadoBadge(estado);

  const inicioEl = row.querySelector(".exec-inicio");
  const fimEl = row.querySelector(".exec-fim");
  const prevInicio = row.dataset.prevInicio || "";
  const prevFim = row.dataset.prevFim || "";

  if (pct <= 0) {
    inicioEl.value = "";
    fimEl.value = "";
  } else {
    inicioEl.value = prevInicio || row.dataset.startedAt || todayISO();
    if (!row.dataset.startedAt && !prevInicio) row.dataset.startedAt = inicioEl.value;
    if (pct >= 100) {
      const prevDone = Number(prevAct(Number(row.dataset.actId))?.pct_conclusao || 0) >= 100;
      fimEl.value = prevDone && prevFim ? prevFim : row.dataset.finishedAt || todayISO();
      if (!row.dataset.finishedAt) row.dataset.finishedAt = fimEl.value;
    } else {
      fimEl.value = "";
      delete row.dataset.finishedAt;
    }
  }
}

function recalcGlobalProgress() {
  const rows = [...document.querySelectorAll(".exec-row[data-act-id]")];
  if (!rows.length) {
    document.getElementById("global_progress_label").textContent = "0%";
    document.getElementById("global_progress_bar").style.width = "0%";
    return 0;
  }
  const sum = rows.reduce((acc, row) => acc + Number(row.querySelector(".exec-pct")?.value || 0), 0);
  const avg = sum / rows.length;
  document.getElementById("global_progress_label").textContent = `${avg.toFixed(0)}%`;
  document.getElementById("global_progress_bar").style.width = `${Math.min(100, avg)}%`;
  return avg;
}

function recalcBudget() {
  let planned = 0;
  let executed = 0;
  document.querySelectorAll("#budget_rows tr[data-cat-id]").forEach((tr) => {
    const input = tr.querySelector(".executed-val");
    const p = Number(input?.dataset.planned || 0);
    const e = Number(input?.value || 0);
    planned += p;
    executed += e;
    const pct = p ? Math.min(100, (e / p) * 100) : 0;
    const cell = tr.querySelector(".pct-cell");
    if (cell) cell.textContent = `${pct.toFixed(0)}%`;
  });
  document.getElementById("sum_planned").textContent = fmtMoney(planned);
  document.getElementById("sum_executed").textContent = fmtMoney(executed);
  const totalPct = planned ? (executed / planned) * 100 : 0;
  document.getElementById("sum_pct").textContent = `${totalPct.toFixed(0)}%`;
  document.getElementById("budget_progress").style.width = `${Math.min(100, totalPct)}%`;
}

function renderSummary(pilar) {
  const objs =
    (pilar.objectivos || []).map((o) => `<li>${escapeHtml(o.descricao)}</li>`).join("") ||
    (pilar.obj_geral ? `<li>${escapeHtml(pilar.obj_geral)}</li>` : "<li class='empty-hint'>Sem objectivos</li>");

  const riscos =
    (pilar.riscos || [])
      .map(
        (r) => `
      <div class="summary-risk">
        <strong>${escapeHtml(r.descricao)}</strong>
        <div class="summary-risk-meta">
          <span class="status-pill neutro">${escapeHtml(enumLabel(r.probabilidade))}</span>
          <span class="status-pill neutro">Impacto: ${escapeHtml(enumLabel(r.impacto))}</span>
        </div>
        ${r.mitigacao ? `<p><span>Mitigacao:</span> ${escapeHtml(r.mitigacao)}</p>` : ""}
      </div>`
      )
      .join("") || `<p class="empty-hint">Sem riscos cadastrados.</p>`;

  const prevPct = previousAval?.progresso != null ? Number(previousAval.progresso) : null;

  document.getElementById("project-summary").innerHTML = `
    <div class="aval-summary-top">
      <div>
        <p class="aval-summary-eyebrow">Projecto</p>
        <h3>${escapeHtml(pilar.nome)}</h3>
        <p class="aval-summary-meta">
          ${escapeHtml(pilar.area || "—")} · ${escapeHtml(pilar.fase || "—")}
          ${pilar.proxima_avaliacao ? ` · Prox. ${escapeHtml(pilar.proxima_avaliacao)}` : ""}
          ${pilar.status ? ` · ${escapeHtml(pilar.status)}` : ""}
        </p>
      </div>
      <a class="btn btn-outline compact" href="/projectos">Ver ficha</a>
    </div>
    <div class="aval-summary-grid">
      <div class="aval-summary-card">
        <h4>Objectivo geral</h4>
        <p>${escapeHtml(pilar.obj_geral || "—")}</p>
        <ul class="list-plain">${objs}</ul>
      </div>
      <div class="aval-summary-card">
        <h4>Orcamento</h4>
        <p><strong>${escapeHtml(pilar.orc_moeda || "MZN")} ${fmtMoney(pilar.orc_aprovado)}</strong></p>
        <p>Fonte: ${escapeHtml(pilar.orc_fonte || "—")}</p>
        <p>Execucao anterior: <strong>${prevPct != null ? `${prevPct.toFixed(0)}%` : "—"}</strong></p>
      </div>
      <div class="aval-summary-card full">
        <h4>Riscos e mitigacao</h4>
        <div class="summary-risks">${riscos}</div>
      </div>
      ${
        pilar.descricao
          ? `<div class="aval-summary-card full"><h4>Descricao</h4><p>${escapeHtml(pilar.descricao)}</p></div>`
          : ""
      }
      ${
        pilar.kpis
          ? `<div class="aval-summary-card"><h4>KPIs</h4><p>${escapeHtml(pilar.kpis)}</p></div>`
          : ""
      }
      ${
        pilar.beneficios
          ? `<div class="aval-summary-card"><h4>Beneficios</h4><p>${escapeHtml(pilar.beneficios)}</p></div>`
          : ""
      }
    </div>`;
}

function snapshotPassosFromDom() {
  return [...document.querySelectorAll(".passo-item")].map((el) => ({
    key: el.dataset.key,
    passo_id: el.dataset.passoId ? Number(el.dataset.passoId) : null,
    descricao: el.querySelector(".passo-desc")?.value || "",
    responsavel: el.querySelector(".passo-resp")?.value || "",
    prazo: el.querySelector(".passo-prazo")?.value || "",
    alcancado: Boolean(el.querySelector(".passo-alcancado")?.checked),
  }));
}

function bindPassoDates(root) {
  const today = todayISO();
  root.querySelectorAll(".passo-prazo").forEach((input) => {
    const raw = input.value || "";
    const ok = raw && raw >= today ? raw : "";
    input.value = ok;
    bindDatePicker(input, {
      defaultDate: ok || null,
      minDate: today,
    });
  });
}

function renderPassosFromRows(rows) {
  const list = document.getElementById("next_steps_list");
  if (!rows.length) {
    list.innerHTML = `<p class="empty-hint">Sem passos em aberto. Adicione acoes para o proximo periodo.</p>`;
    return;
  }
  list.innerHTML = `
    <div class="passo-list">
      <div class="passo-list-head">
        <span>Acao</span>
        <span>Responsavel</span>
        <span>Prazo</span>
        <span>Estado</span>
        <span></span>
      </div>
      ${rows
        .map(
          (p) => `
        <div class="passo-item" data-key="${escapeHtml(p.key)}" ${
            p.passo_id ? `data-passo-id="${p.passo_id}"` : ""
          }>
          <input class="passo-desc" type="text" value="${escapeHtml(p.descricao)}" placeholder="Descricao da acao" ${
            p.passo_id ? "readonly" : ""
          } />
          <input class="passo-resp" type="text" value="${escapeHtml(p.responsavel)}" placeholder="Responsavel" />
          <input class="passo-prazo" type="text" value="${escapeHtml(p.prazo || "")}" placeholder="Seleccione a data" />
          <label class="passo-done">
            <input class="passo-alcancado" type="checkbox" ${p.alcancado ? "checked" : ""} />
            <span>Concluido</span>
          </label>
          <div class="passo-actions">
            ${
              p.passo_id
                ? ""
                : `<button type="button" class="icon-btn compact danger" data-remove-passo="${escapeHtml(
                    p.key
                  )}" title="Remover"><i class="bi bi-trash"></i></button>`
            }
          </div>
        </div>`
        )
        .join("")}
    </div>`;

  list.querySelectorAll("[data-remove-passo]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const next = snapshotPassosFromDom().filter((p) => p.key !== btn.dataset.removePasso);
      renderPassosFromRows(next);
    });
  });
  bindPassoDates(list);
}

function seedPassos(pilar) {
  const doneIds = new Set(
    (previousAval?.proximos_passos || []).filter((p) => p.alcancado).map((p) => p.passo_id)
  );

  const openMaster = (pilar.proximos_passos || [])
    .filter((p) => !doneIds.has(p.id))
    .map((p) => ({
      key: `m-${p.id}`,
      passo_id: p.id,
      descricao: p.descricao || "",
      responsavel: p.responsavel || "",
      prazo: p.prazo || "",
      alcancado: false,
    }));

  renderPassosFromRows(openMaster);
}

function renderPendingAnexos() {
  const host = document.getElementById("anexos_pending");
  if (!host) return;
  if (!pendingAnexos.length) {
    host.innerHTML = `<p class="empty-hint">Nenhum ficheiro seleccionado.</p>`;
    return;
  }
  host.innerHTML = `
    <ul class="anexo-pending-ul">
      ${pendingAnexos
        .map(
          (f, i) => `
        <li>
          <i class="bi bi-file-earmark"></i>
          <div>
            <strong>${escapeHtml(f.name)}</strong>
            <span>${formatBytes(f.size)}</span>
          </div>
          <button type="button" class="icon-btn compact danger" data-remove-anexo="${i}" title="Remover">
            <i class="bi bi-x-lg"></i>
          </button>
        </li>`
        )
        .join("")}
    </ul>`;
  host.querySelectorAll("[data-remove-anexo]").forEach((btn) => {
    btn.addEventListener("click", () => {
      pendingAnexos.splice(Number(btn.dataset.removeAnexo), 1);
      renderPendingAnexos();
    });
  });
}

document.getElementById("anexo_input")?.addEventListener("change", (e) => {
  const input = e.target;
  const files = [...(input.files || [])];
  const max = 12 * 1024 * 1024;
  for (const f of files) {
    if (f.size > max) {
      toast(`"${f.name}" excede 12 MB.`, "error");
      continue;
    }
    if (pendingAnexos.some((x) => x.name === f.name && x.size === f.size)) continue;
    pendingAnexos.push(f);
  }
  input.value = "";
  renderPendingAnexos();
});

function renderRisks(pilar) {
  const host = document.getElementById("risks_list");
  const riscos = pilar.riscos || [];
  if (!riscos.length) {
    host.innerHTML = `<p class="empty-hint">Sem riscos no projecto</p>`;
    return;
  }
  host.innerHTML = riscos
    .map(
      (r) => `
    <article class="risk-card" data-risco-id="${r.id}">
      <div class="risk-card-top">
        <strong>${escapeHtml(r.descricao)}</strong>
        <div class="risk-card-meta">
          <span class="status-pill neutro">${escapeHtml(enumLabel(r.probabilidade))}</span>
          <span class="status-pill neutro">Impacto: ${escapeHtml(enumLabel(r.impacto))}</span>
        </div>
        ${r.mitigacao ? `<p class="risk-card-mit">Mitigacao: ${escapeHtml(r.mitigacao)}</p>` : ""}
      </div>
      <label class="risk-obs-field">
        <span>Observacao do periodo</span>
        <textarea class="risco-obs" rows="3" placeholder="Observacao deste periodo"></textarea>
      </label>
    </article>`
    )
    .join("");
}

function renderForm(pilar) {
  currentPilar = pilar;
  pendingAnexos = [];
  renderPendingAnexos();
  renderSummary(pilar);

  const exec = document.getElementById("execution_list");
  const acts = pilar.actividades || [];
  if (!acts.length) {
    exec.innerHTML = `<p class="empty-hint">Sem actividades no projecto — configure na base de projectos.</p>`;
  } else {
    exec.innerHTML = `
      <div class="table-wrap">
        <table class="aval-table">
          <thead>
            <tr>
              <th>Actividade</th>
              <th>Estado</th>
              <th>% Conclusao</th>
              <th>Inicio real</th>
              <th>Fim real</th>
            </tr>
          </thead>
          <tbody>
            ${acts
              .map((a) => {
                const prev = prevAct(a.id);
                const minPct = Number(prev?.pct_conclusao || 0);
                const startPct = minPct;
                const prevInicio = prev?.data_inicio_real || "";
                const prevFim = prev?.data_fim_real || "";
                return `
              <tr class="exec-row" data-act-id="${a.id}" data-prev-inicio="${escapeHtml(
                  prevInicio
                )}" data-prev-fim="${escapeHtml(prevFim)}">
                <td>
                  <strong>${escapeHtml(a.nome)}</strong>
                  ${a.responsavel ? `<div class="muted-cell">${escapeHtml(a.responsavel)}</div>` : ""}
                </td>
                <td class="exec-estado-badge">${estadoBadge(estadoFromPct(startPct))}</td>
                <td>
                  <input class="exec-pct" type="number" min="0" max="100" step="1" value="${startPct}" data-min="${minPct}" />
                </td>
                <td><input class="exec-inicio" type="text" readonly value="" placeholder="—" /></td>
                <td><input class="exec-fim" type="text" readonly value="" placeholder="—" /></td>
              </tr>`;
              })
              .join("")}
          </tbody>
        </table>
      </div>`;

    exec.querySelectorAll(".exec-row").forEach((row) => {
      applyActivityDerived(row);
      row.querySelector(".exec-pct")?.addEventListener("input", () => {
        applyActivityDerived(row);
        recalcGlobalProgress();
      });
    });
  }
  recalcGlobalProgress();

  const budgetRows = document.getElementById("budget_rows");
  const cats = pilar.orcamento_categorias || [];
  budgetRows.innerHTML =
    cats
      .map((c) => {
        const prev = prevOrc(c.id);
        const minVal = Number(prev?.valor_executado || 0);
        return `
      <tr data-cat-id="${c.id}">
        <td>${escapeHtml(c.categoria)}</td>
        <td class="planned-cell">${fmtMoney(c.valor_alocado)}</td>
        <td>
          <input class="executed-val" type="number" min="0" step="0.01" value="${minVal}" data-planned="${c.valor_alocado}" data-min="${minVal}" />
        </td>
        <td class="pct-cell">0%</td>
      </tr>`;
      })
      .join("") || `<tr><td colspan="4" class="empty-hint">Sem rubricas no projecto</td></tr>`;

  budgetRows.querySelectorAll(".executed-val").forEach((input) => {
    input.addEventListener("input", recalcBudget);
  });
  recalcBudget();

  seedPassos(pilar);
  renderRisks(pilar);

  empty.hidden = true;
  form.hidden = false;
}

document.getElementById("btn-add-passo")?.addEventListener("click", () => {
  if (!currentPilar) return;
  const rows = snapshotPassosFromDom();
  rows.push({
    key: `n-${Date.now()}`,
    passo_id: null,
    descricao: "",
    responsavel: "",
    prazo: "",
    alcancado: false,
  });
  renderPassosFromRows(rows);
});

function buildPayload() {
  const pilarId = currentPilar?.id;
  if (!pilarId) throw new Error("Seleccione um pilar.");

  const progresso = recalcGlobalProgress();

  const actividades = [...document.querySelectorAll(".exec-row[data-act-id]")].map((el) => {
    const input = el.querySelector(".exec-pct");
    const pct = Number(input?.value || 0);
    const min = Number(input?.dataset.min || 0);
    if (pct < min) {
      throw new Error(
        `A % de conclusao nao pode ser inferior a ${min}% (valor da avaliacao anterior).`
      );
    }
    if (pct < 0 || pct > 100) throw new Error("A % de conclusao deve estar entre 0 e 100.");
    return {
      pilar_actividade_id: Number(el.dataset.actId),
      estado: estadoFromPct(pct),
      pct_conclusao: pct,
      data_inicio_real: el.querySelector(".exec-inicio")?.value || null,
      data_fim_real: el.querySelector(".exec-fim")?.value || null,
      obs_execucao: null,
    };
  });

  const orcamentos = [...document.querySelectorAll("#budget_rows tr[data-cat-id]")].map((tr) => {
    const input = tr.querySelector(".executed-val");
    const val = Number(input?.value || 0);
    const min = Number(input?.dataset.min || 0);
    if (val < min) {
      throw new Error(
        `Valor executado abaixo do minimo cumulativo (${fmtMoney(min)}) numa rubrica.`
      );
    }
    return {
      categoria_id: Number(tr.dataset.catId),
      valor_executado: String(val),
      forma_execucao: null,
      obs: null,
    };
  });

  const proximos_passos = [...document.querySelectorAll(".passo-item")].map((el) => {
    const descricao = el.querySelector(".passo-desc")?.value?.trim() || "";
    const responsavel = el.querySelector(".passo-resp")?.value?.trim() || "";
    const prazo = el.querySelector(".passo-prazo")?.value || null;
    const passoId = el.dataset.passoId ? Number(el.dataset.passoId) : null;
    const alcancado = Boolean(el.querySelector(".passo-alcancado")?.checked);
    if (!descricao) throw new Error("Indique a descricao de todos os proximos passos.");
    if (prazo && prazo < todayISO()) {
      throw new Error("O prazo dos proximos passos deve ser uma data futura (ou hoje).");
    }
    return {
      passo_id: passoId,
      descricao,
      responsavel,
      prazo: prazo || null,
      alcancado,
      observacao: null,
    };
  });

  return {
    pilar_id: pilarId,
    estado_geral: "",
    desafios: "",
    licoes: "",
    orc_obs: null,
    recomendacoes: null,
    comentarios: null,
    progresso,
    assinatura: null,
    data_sub: todayISO(),
    actividades,
    orcamentos,
    riscos: [...document.querySelectorAll(".risk-card[data-risco-id]")].map((el) => ({
      risco_id: Number(el.dataset.riscoId),
      observacao: el.querySelector(".risco-obs")?.value || null,
    })),
    proximos_passos,
  };
}

async function loadPilar(id) {
  const url = new URL(window.location.href);
  url.searchParams.set("pilar", String(id));
  window.history.replaceState({}, "", url);
  empty.hidden = false;
  empty.innerHTML = `<i class="bi bi-hourglass-split"></i><p>A carregar projecto...</p>`;
  form.hidden = true;
  try {
    const [{ pilar }, latest] = await Promise.all([
      api(`/pilares/${id}`),
      api(`/avaliacoes/latest/${id}`).catch(() => ({ avaliacao: null })),
    ]);
    previousAval = latest?.avaliacao || null;
    renderForm(pilar);
  } catch (err) {
    toast(err.message || "Erro ao carregar projecto", "error");
    empty.innerHTML = `<i class="bi bi-x-circle"></i><p>${escapeHtml(err.message || "Erro")}</p>`;
  }
}

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = document.getElementById("btn_submit");
  if (!submitBtn) return;
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> A submeter...';
  try {
    const payload = buildPayload();
    const result = await api("/avaliacoes", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (pendingAnexos.length) {
      submitBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> A carregar anexos...';
      const fd = new FormData();
      pendingAnexos.forEach((f) => fd.append("files", f, f.name));
      await apiForm(`/avaliacoes/${result.id}/anexos`, fd);
    }

    toast(result.message || "Avaliacao submetida.", "success");
    setTimeout(() => {
      window.location.href = `/avaliacoes?ver=${result.id}`;
    }, 700);
  } catch (err) {
    toast(err.message || "Falha ao submeter", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="bi bi-send"></i> Submeter avaliacao';
  }
});

async function init() {
  try {
    const { pilares } = await api("/pilares");
    if (!pilares?.length) {
      empty.innerHTML = `<i class="bi bi-inbox"></i><p>Sem pilares activos.</p>`;
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const fromQuery = Number(params.get("pilar"));
    const startId = pilares.some((p) => p.id === fromQuery) ? fromQuery : pilares[0].id;
    picker = mountPilarPicker(pickerHost, {
      pilares,
      selectedId: startId,
      onChange: (id) => loadPilar(id),
    });
    await loadPilar(startId);
  } catch (err) {
    empty.innerHTML = `<i class="bi bi-x-circle"></i><p>${escapeHtml(err.message || "Erro")}</p>`;
  }
}

init();
