/** Base de projectos — cards com pesquisa e paginacao. */
import { api } from "../api.js";
import { filterByQuery, mountSearchPager, paginate } from "../components/list-kit.js";
import { bootPage } from "../shell.js";
import { setLoading, toast } from "../ui.js";

const { user } = await bootPage({
  page: "projectos",
  title: "Base de projectos",
  subtitle: "Cadastro mestre dos pilares",
});

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function money(n) {
  return Number(n || 0).toLocaleString("pt-MZ", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function fmtDate(iso) {
  if (!iso) return "";
  const raw = String(iso).slice(0, 10);
  const [y, m, d] = raw.split("-");
  if (!y || !m || !d) return raw;
  return `${d}/${m}/${y}`;
}

function statusPill(status) {
  const s = String(status || "activo");
  const cls = s === "inactivo" ? "neutro" : "ok";
  return `<span class="status-pill ${cls}">${escapeHtml(s)}</span>`;
}

function prioridadePill(p) {
  const v = String(p || "media");
  const map = { alta: "atraso", media: "warn", baixa: "neutro" };
  return `<span class="status-pill ${map[v] || "neutro"}">${escapeHtml(v)}</span>`;
}

function riscoPill(nivel) {
  const v = String(nivel || "").toLowerCase();
  const map = { alta: "atraso", media: "warn", baixa: "ok", alto: "atraso", medio: "warn", baixo: "ok" };
  return `<span class="status-pill ${map[v] || "neutro"}">${escapeHtml(v || "—")}</span>`;
}

const listEl = document.getElementById("projectos-list");
const detailEl = document.getElementById("projecto-detail");
let allItems = [];

const pager = mountSearchPager(document.getElementById("projectos-controls"), {
  pageSize: 9,
  placeholder: "Pesquisar nome, area, fase, status...",
  onChange: renderList,
});

function emptyBlock(msg) {
  return `<p class="ficha-empty">${escapeHtml(msg)}</p>`;
}

async function showDetail(id) {
  detailEl.hidden = false;
  setLoading(detailEl, "A carregar ficha...");
  try {
    const { pilar } = await api(`/pilares/${id}`);
    const canEdit =
      user?.role === "admin" || (user?.permissions || []).includes("projectos.manage");

    const acts = (pilar.actividades || [])
      .map((a) => {
        const cancelled = a.status === "cancelada";
        const ini = fmtDate(a.data_inicio_prevista);
        const fim = fmtDate(a.data_fim_prevista);
        const dates =
          ini || fim
            ? `<span class="ficha-item-dates"><i class="bi bi-calendar3"></i> ${escapeHtml(
                ini || "?"
              )} → ${escapeHtml(fim || "?")}</span>`
            : "";
        return `
          <li class="ficha-item ${cancelled ? "is-cancelled" : ""}">
            <div class="ficha-item-main">
              <strong>${escapeHtml(a.nome)}</strong>
              <span class="ficha-item-sub">${escapeHtml(a.responsavel || "Sem responsavel")}</span>
              ${dates}
            </div>
            <div class="ficha-item-side">
              ${cancelled ? `<span class="status-pill cancel">cancelada</span>` : prioridadePill(a.prioridade)}
            </div>
          </li>`;
      })
      .join("");

    const cats = (pilar.orcamento_categorias || [])
      .map(
        (c) => `
        <li class="ficha-item ficha-item-orc">
          <span class="ficha-item-label">${escapeHtml(c.categoria)}</span>
          <strong class="ficha-item-value">${money(c.valor_alocado)}</strong>
        </li>`
      )
      .join("");

    const risks = (pilar.riscos || [])
      .map(
        (r) => `
        <li class="ficha-item ficha-item-risk">
          <div class="ficha-item-main">
            <strong>${escapeHtml(r.descricao)}</strong>
            ${
              r.mitigacao
                ? `<span class="ficha-item-sub pre-wrap">Mitigacao: ${escapeHtml(r.mitigacao)}</span>`
                : ""
            }
          </div>
          <div class="ficha-item-side">
            ${riscoPill(r.probabilidade)}
            <span class="ficha-impact">Impacto ${escapeHtml(r.impacto || "—")}</span>
          </div>
        </li>`
      )
      .join("");

    detailEl.innerHTML = `
      <article class="ficha-projecto">
        <header class="ficha-head">
          <div>
            <p class="ficha-eyebrow">Ficha do projecto</p>
            <h3>${escapeHtml(pilar.nome)}</h3>
            <div class="ficha-meta">
              ${statusPill(pilar.status)}
              <span class="ficha-meta-dot">${escapeHtml(pilar.area || "—")}</span>
              <span class="ficha-meta-dot">${escapeHtml(pilar.fase || "—")}</span>
              ${
                pilar.proxima_avaliacao
                  ? `<span class="ficha-meta-dot">Prox. ${escapeHtml(fmtDate(pilar.proxima_avaliacao))}</span>`
                  : ""
              }
            </div>
          </div>
          ${
            canEdit
              ? `<a class="btn btn-outline compact" href="/admin/projectos/${pilar.id}"><i class="bi bi-pencil"></i> Editar</a>`
              : ""
          }
        </header>

        <div class="ficha-overview">
          <div class="ficha-block">
            <h4><i class="bi bi-info-circle"></i> Contexto</h4>
            <dl class="ficha-dl">
              <div><dt>Area</dt><dd>${escapeHtml(pilar.area || "—")}</dd></div>
              <div><dt>Fase</dt><dd>${escapeHtml(pilar.fase || "—")}</dd></div>
              <div><dt>Moeda</dt><dd>${escapeHtml(pilar.orc_moeda || "MZN")}</dd></div>
              <div><dt>Fonte</dt><dd>${escapeHtml(pilar.orc_fonte || "—")}</dd></div>
            </dl>
            ${
              pilar.descricao
                ? `<p class="ficha-text pre-wrap">${escapeHtml(pilar.descricao)}</p>`
                : ""
            }
          </div>
          <div class="ficha-block">
            <h4><i class="bi bi-bullseye"></i> Objectivo geral</h4>
            <p class="ficha-text pre-wrap">${escapeHtml(pilar.obj_geral || "—")}</p>
          </div>
          <div class="ficha-block ficha-block-accent">
            <h4><i class="bi bi-cash-coin"></i> Orcamento global</h4>
            <p class="ficha-orc-total">${escapeHtml(pilar.orc_moeda || "MZN")} ${money(
              pilar.orc_aprovado
            )}</p>
            <p class="ficha-hint">Soma das rubricas orcamentais</p>
          </div>
        </div>

        ${
          pilar.kpis || pilar.beneficios
            ? `<div class="ficha-overview ficha-overview-2">
                ${
                  pilar.kpis
                    ? `<div class="ficha-block"><h4><i class="bi bi-speedometer2"></i> KPIs</h4><p class="ficha-text pre-wrap">${escapeHtml(
                        pilar.kpis
                      )}</p></div>`
                    : ""
                }
                ${
                  pilar.beneficios
                    ? `<div class="ficha-block"><h4><i class="bi bi-stars"></i> Beneficios</h4><p class="ficha-text pre-wrap">${escapeHtml(
                        pilar.beneficios
                      )}</p></div>`
                    : ""
                }
              </div>`
            : ""
        }

        <section class="ficha-section">
          <header class="ficha-section-head">
            <h4><i class="bi bi-list-task"></i> Actividades planeadas</h4>
            <span class="ficha-count">${(pilar.actividades || []).length}</span>
          </header>
          ${acts ? `<ul class="ficha-list">${acts}</ul>` : emptyBlock("Sem actividades planeadas.")}
        </section>

        <section class="ficha-section">
          <header class="ficha-section-head">
            <h4><i class="bi bi-pie-chart"></i> Rubricas orcamentais</h4>
            <span class="ficha-count">${(pilar.orcamento_categorias || []).length}</span>
          </header>
          ${
            cats
              ? `<ul class="ficha-list">${cats}</ul>`
              : emptyBlock("Sem rubricas orcamentais.")
          }
        </section>

        <section class="ficha-section">
          <header class="ficha-section-head">
            <h4><i class="bi bi-exclamation-triangle"></i> Riscos</h4>
            <span class="ficha-count">${(pilar.riscos || []).length}</span>
          </header>
          ${risks ? `<ul class="ficha-list">${risks}</ul>` : emptyBlock("Sem riscos identificados.")}
        </section>
      </article>`;
    detailEl.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    toast(err.message || "Erro", "error");
    detailEl.innerHTML = `<p class="empty-hint">${escapeHtml(err.message)}</p>`;
  }
}

function renderList() {
  const filtered = filterByQuery(allItems, pager.query, (p) => [
    p.nome,
    p.area,
    p.fase,
    p.status,
    p.proxima_avaliacao,
  ]);
  const page = paginate(filtered, pager.page, pager.pageSize);
  pager.setMeta(page);

  if (!page.total) {
    listEl.innerHTML = `<div class="no-data compact"><i class="bi bi-inbox"></i><p>Sem projectos.</p></div>`;
    return;
  }

  listEl.innerHTML = page.items
    .map(
      (p) => `
      <button type="button" class="info-card" data-id="${p.id}">
        <div>
          <strong>${escapeHtml(p.nome)}</strong>
          <span>${escapeHtml(p.area || "—")} · ${escapeHtml(p.fase || "—")}</span>
          <div class="card-meta">
            ${statusPill(p.status)}
            <span class="status-pill neutro">Prox. ${escapeHtml(fmtDate(p.proxima_avaliacao) || "—")}</span>
          </div>
        </div>
        <div class="card-foot"><span>Abrir ficha</span><i class="bi bi-chevron-right"></i></div>
      </button>`
    )
    .join("");
}

listEl.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-id]");
  if (btn) showDetail(Number(btn.dataset.id));
});

setLoading(listEl);
try {
  const { pilares } = await api("/pilares");
  allItems = pilares || [];
  renderList();
} catch (err) {
  toast(err.message || "Erro", "error");
  listEl.innerHTML = `<div class="no-data compact"><p>${escapeHtml(err.message)}</p></div>`;
}
