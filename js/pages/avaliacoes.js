/** Arquivo de avaliacoes — listagem + detalhe read-only. */
import { api, formatBytes } from "../api.js";
import { enhanceSelect } from "../components/styled-select.js";
import { filterByQuery, mountSearchPager, paginate } from "../components/list-kit.js";
import { bootPage } from "../shell.js";
import { setLoading, toast } from "../ui.js";

const { user } = await bootPage({
  page: "avaliacoes",
  title: "Avaliacoes",
  subtitle: "Arquivo e consulta",
});

const canValidate =
  user?.role === "admin" || (user?.permissions || []).includes("avaliacao.validate");

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fmtMoney(n) {
  return Number(n || 0).toLocaleString("pt-MZ", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const listEl = document.getElementById("arquivo-list");
const filterEl = document.getElementById("filter-pilar");
const detailPanel = document.getElementById("arquivo-detail");
const detailBody = document.getElementById("detail-body");
const detailTitle = document.getElementById("detail-title");

let allRows = [];

const pager = mountSearchPager(document.getElementById("arquivo-controls"), {
  pageSize: 10,
  placeholder: "Pesquisar projecto, autor, data...",
  onChange: renderList,
});

function renderList() {
  const fid = filterEl.value;
  let rows = fid ? allRows.filter((r) => String(r.pilar_id) === fid) : allRows;
  rows = filterByQuery(rows, pager.query, (r) => [
    r.pilar_nome,
    r.autor,
    r.data_sub,
    r.progresso,
  ]);
  const page = paginate(rows, pager.page, pager.pageSize);
  pager.setMeta(page);

  if (!page.total) {
    listEl.innerHTML = `<div class="no-data compact"><i class="bi bi-inbox"></i><p>Sem avaliacoes no arquivo.</p></div>`;
    return;
  }
  listEl.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Data</th>
          <th>Projecto</th>
          <th>Progresso</th>
          <th>Estado</th>
          <th>Autor</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        ${page.items
          .map(
            (r) => `
          <tr>
            <td>${escapeHtml(r.data_sub || "—")}</td>
            <td><strong>${escapeHtml(r.pilar_nome)}</strong></td>
            <td><span class="status-pill ok">${Number(r.progresso || 0).toFixed(0)}%</span></td>
            <td><span class="status-pill ${r.status === "validada" ? "ok" : r.status === "reaberta" ? "warn" : "neutro"}">${escapeHtml(r.status || "submetida")}</span></td>
            <td>${escapeHtml(r.autor || "—")}</td>
            <td><button type="button" class="btn btn-outline compact" data-ver="${r.id}">Ver</button></td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>`;

  listEl.querySelectorAll("[data-ver]").forEach((btn) => {
    btn.addEventListener("click", () => openDetail(Number(btn.dataset.ver)));
  });
}

function estadoLabel(estado) {
  const e = String(estado || "");
  if (e === "em_progresso") return "Em progresso";
  if (e === "concluida") return "Concluida";
  if (e === "pendente") return "Pendente";
  return e.replaceAll("_", " ") || "—";
}

function estadoClass(estado) {
  if (estado === "concluida") return "ok";
  if (estado === "em_progresso") return "warn";
  return "neutro";
}

function renderAnexosBlock(anexos) {
  if (!(anexos || []).length) {
    return `<p class="empty-hint">Sem anexos nesta avaliacao.</p>`;
  }
  return `
    <ul class="anexo-list">
      ${(anexos || [])
        .map(
          (f) => `
        <li>
          <i class="bi bi-paperclip"></i>
          <div>
            <strong>${escapeHtml(f.original_name)}</strong>
            <span>${formatBytes(f.size_bytes)} · ${escapeHtml(f.uploaded_by || "—")}</span>
          </div>
          <a class="btn btn-outline compact" href="${escapeHtml(f.download_url || `/api/v1/anexos/${f.id}/download`)}" download>
            <i class="bi bi-download"></i> Transferir
          </a>
        </li>`
        )
        .join("")}
    </ul>`;
}

async function openDetail(id) {
  detailPanel.hidden = false;
  detailTitle.textContent = "A carregar...";
  detailBody.innerHTML = `<div class="no-data compact"><i class="bi bi-hourglass-split"></i><p>A carregar...</p></div>`;
  detailPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  const url = new URL(window.location.href);
  url.searchParams.set("ver", String(id));
  window.history.replaceState({}, "", url);

  try {
    const { avaliacao: a } = await api(`/avaliacoes/${id}`);
    detailTitle.textContent = `${a.pilar_nome} · ${a.data_sub || "sem data"}`;
    const acts = a.actividades || [];
    const orcs = a.orcamentos || [];
    const riscos = a.riscos || [];
    const passos = a.proximos_passos || [];
    const anexos = a.anexos || [];

    detailBody.innerHTML = `
      <div class="aval-detail">
        <div class="aval-detail-hero">
          <div>
            <p class="aval-detail-eyebrow">Acompanhamento de execucao</p>
            <h4>${escapeHtml(a.pilar_nome)}</h4>
            <p class="aval-detail-meta">Submetida em ${escapeHtml(a.data_sub || "—")} · ${escapeHtml(a.autor || "—")} · <span class="status-pill ${a.status === "validada" ? "ok" : a.status === "reaberta" ? "warn" : "neutro"}">${escapeHtml(a.status || "submetida")}</span></p>
          </div>
          <div class="aval-detail-progress">
            <span>Progresso</span>
            <strong>${Number(a.progresso || 0).toFixed(0)}%</strong>
            <div class="progress-bar-wrap compact"><div class="progress-bar" style="width:${Math.min(100, Number(a.progresso || 0))}%"></div></div>
            <div class="row-actions" style="margin-top:10px">
              ${
                canValidate && a.status !== "validada"
                  ? `<button type="button" class="btn btn-primary compact" id="btn-validate-aval"><i class="bi bi-check2-circle"></i> Validar</button>`
                  : ""
              }
              ${
                canValidate && a.status === "validada"
                  ? `<button type="button" class="btn btn-outline compact" id="btn-reopen-aval"><i class="bi bi-unlock"></i> Reabrir</button>`
                  : ""
              }
              ${
                a.status !== "validada"
                  ? `<a class="btn btn-outline compact" href="/avaliacao?pilar=${a.pilar_id}&edit=${a.id}"><i class="bi bi-pencil"></i> Editar</a>`
                  : ""
              }
            </div>
          </div>
        </div>

        <section class="aval-detail-section">
          <h5><i class="bi bi-list-check"></i> Actividades (${acts.length})</h5>
          ${
            acts.length
              ? `<div class="table-wrap"><table class="act-detail-table">
                  <thead><tr><th>Actividade</th><th>Estado</th><th>%</th><th>Inicio</th><th>Fim</th></tr></thead>
                  <tbody>
                    ${acts
                      .map(
                        (x) => `
                      <tr>
                        <td><strong>${escapeHtml(x.nome || "—")}</strong></td>
                        <td><span class="status-pill ${estadoClass(x.estado)}">${escapeHtml(estadoLabel(x.estado))}</span></td>
                        <td>${x.pct_conclusao ?? 0}%</td>
                        <td>${escapeHtml(x.data_inicio_real || "—")}</td>
                        <td>${escapeHtml(x.data_fim_real || "—")}</td>
                      </tr>`
                      )
                      .join("")}
                  </tbody>
                </table></div>`
              : `<p class="empty-hint">Sem actividades nesta avaliacao.</p>`
          }
        </section>

        <section class="aval-detail-section">
          <h5><i class="bi bi-cash-stack"></i> Orcamento (${orcs.length})</h5>
          ${
            orcs.length
              ? `<div class="table-wrap"><table class="act-detail-table">
                  <thead><tr><th>Rubrica</th><th>Executado</th></tr></thead>
                  <tbody>
                    ${orcs
                      .map(
                        (o) => `
                      <tr>
                        <td><strong>${escapeHtml(o.categoria || "—")}</strong></td>
                        <td>${fmtMoney(o.valor_executado)}</td>
                      </tr>`
                      )
                      .join("")}
                  </tbody>
                </table></div>`
              : `<p class="empty-hint">Sem dados orcamentais.</p>`
          }
        </section>

        <section class="aval-detail-section">
          <h5><i class="bi bi-signpost-2"></i> Proximos passos (${passos.length})</h5>
          ${
            passos.length
              ? `<div class="table-wrap"><table class="act-detail-table">
                  <thead><tr><th>Acao</th><th>Responsavel</th><th>Prazo</th><th>Estado</th></tr></thead>
                  <tbody>
                    ${passos
                      .map(
                        (p) => `
                      <tr>
                        <td><strong>${escapeHtml(p.descricao || "—")}</strong></td>
                        <td>${escapeHtml(p.responsavel || "—")}</td>
                        <td>${escapeHtml(p.prazo || "—")}</td>
                        <td><span class="status-pill ${p.alcancado ? "ok" : "warn"}">${p.alcancado ? "Concluido" : "Em aberto"}</span></td>
                      </tr>`
                      )
                      .join("")}
                  </tbody>
                </table></div>`
              : `<p class="empty-hint">Sem proximos passos registados.</p>`
          }
        </section>

        <section class="aval-detail-section">
          <h5><i class="bi bi-exclamation-triangle"></i> Riscos (${riscos.length})</h5>
          ${
            riscos.length
              ? `<div class="risk-list">
                  ${riscos
                    .map(
                      (r) => `
                    <article class="risk-card">
                      <div class="risk-card-top">
                        <strong>${escapeHtml(r.descricao || "—")}</strong>
                        <div class="risk-card-meta">
                          <span class="status-pill neutro">${escapeHtml(r.probabilidade || "—")}</span>
                          <span class="status-pill neutro">Impacto: ${escapeHtml(r.impacto || "—")}</span>
                        </div>
                        ${r.mitigacao ? `<p class="risk-card-mit">Mitigacao: ${escapeHtml(r.mitigacao)}</p>` : ""}
                        ${r.observacao ? `<p class="risk-card-mit">Obs. periodo: ${escapeHtml(r.observacao)}</p>` : ""}
                      </div>
                    </article>`
                    )
                    .join("")}
                </div>`
              : `<p class="empty-hint">Sem riscos nesta avaliacao.</p>`
          }
        </section>

        <section class="aval-detail-section">
          <h5><i class="bi bi-paperclip"></i> Anexos (${anexos.length})</h5>
          ${renderAnexosBlock(anexos)}
        </section>

        <div class="submit-bar" style="margin-top:8px">
          <a class="btn btn-primary compact" href="/dashboard?pilar=${a.pilar_id}">Ver resultados</a>
          <a class="btn btn-outline compact" href="/avaliacao?pilar=${a.pilar_id}">Nova avaliacao deste projecto</a>
          <a class="btn btn-outline compact" href="/anexos?q=${encodeURIComponent(a.pilar_nome || "")}">Ver anexos</a>
        </div>
      </div>`;

    detailBody.querySelector("#btn-validate-aval")?.addEventListener("click", async () => {
      if (!confirm("Validar esta avaliacao? Deixa de ser editavel.")) return;
      try {
        await api(`/avaliacoes/${id}/validate`, { method: "POST", body: "{}" });
        toast("Avaliacao validada.", "success");
        const { avaliacoes } = await api("/avaliacoes");
        allRows = avaliacoes || [];
        renderList();
        openDetail(id);
      } catch (err) {
        toast(err.message || "Erro", "error");
      }
    });
    detailBody.querySelector("#btn-reopen-aval")?.addEventListener("click", async () => {
      if (!confirm("Reabrir esta avaliacao para edicao?")) return;
      try {
        await api(`/avaliacoes/${id}/reopen`, { method: "POST", body: "{}" });
        toast("Avaliacao reaberta.", "success");
        const { avaliacoes } = await api("/avaliacoes");
        allRows = avaliacoes || [];
        renderList();
        openDetail(id);
      } catch (err) {
        toast(err.message || "Erro", "error");
      }
    });
  } catch (err) {
    toast(err.message || "Erro", "error");
    detailBody.innerHTML = `<div class="no-data compact"><p>${escapeHtml(err.message)}</p></div>`;
  }
}

document.getElementById("btn-close-detail")?.addEventListener("click", () => {
  detailPanel.hidden = true;
  const url = new URL(window.location.href);
  url.searchParams.delete("ver");
  window.history.replaceState({}, "", url);
});

filterEl?.addEventListener("change", () => {
  renderList();
});

async function init() {
  setLoading(listEl, "A carregar arquivo...");
  try {
    const [{ pilares }, { avaliacoes }] = await Promise.all([
      api("/pilares"),
      api("/avaliacoes"),
    ]);
    allRows = avaliacoes || [];
    filterEl.innerHTML =
      `<option value="">Todos</option>` +
      (pilares || [])
        .map((p) => `<option value="${p.id}">${escapeHtml(p.nome)}</option>`)
        .join("");
    enhanceSelect(filterEl);
    renderList();
    const ver = Number(new URLSearchParams(window.location.search).get("ver"));
    if (ver) openDetail(ver);
  } catch (err) {
    toast(err.message || "Erro", "error");
    listEl.innerHTML = `<div class="no-data compact"><p>${escapeHtml(err.message)}</p></div>`;
  }
}

init();
