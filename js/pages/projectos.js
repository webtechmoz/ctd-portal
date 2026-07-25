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
    .replaceAll(">", "&gt;");
}

function money(n) {
  return Number(n || 0).toLocaleString("pt-MZ");
}

const listEl = document.getElementById("projectos-list");
const detailEl = document.getElementById("projecto-detail");
let allItems = [];

const pager = mountSearchPager(document.getElementById("projectos-controls"), {
  pageSize: 9,
  placeholder: "Pesquisar nome, area, fase, status...",
  onChange: renderList,
});

async function showDetail(id) {
  detailEl.hidden = false;
  setLoading(detailEl, "A carregar ficha...");
  try {
    const { pilar } = await api(`/pilares/${id}`);
    const objs = (pilar.objectivos || [])
      .map((o) => o.descricao?.trim())
      .filter((d) => d && d !== (pilar.obj_geral || "").trim())
      .map((d) => `<li>${escapeHtml(d)}</li>`)
      .join("");
    const acts = (pilar.actividades || [])
      .map((a) => {
        const cancelled = a.status === "cancelada";
        const dates =
          a.data_inicio_prevista || a.data_fim_prevista
            ? ` · ${a.data_inicio_prevista || "?"} → ${a.data_fim_prevista || "?"}`
            : "";
        return `<li class="${cancelled ? "is-cancelled-text" : ""}"><strong>${escapeHtml(a.nome)}</strong> — ${escapeHtml(
          a.responsavel || "—"
        )}${escapeHtml(dates)}${cancelled ? " <em>(cancelada)</em>" : ""}</li>`;
      })
      .join("") || "<li class='empty-hint'>Sem actividades</li>";
    const cats = (pilar.orcamento_categorias || [])
      .map((c) => `<li>${escapeHtml(c.categoria)}: ${money(c.valor_alocado)}</li>`)
      .join("") || "<li class='empty-hint'>Sem rubricas</li>";
    const risks = (pilar.riscos || [])
      .map(
        (r) =>
          `<li>${escapeHtml(r.descricao)} <span class="badge ${r.probabilidade}">${r.probabilidade}</span></li>`
      )
      .join("") || "<li class='empty-hint'>Sem riscos</li>";

    detailEl.innerHTML = `
      <div class="panel-head">
        <h3>${escapeHtml(pilar.nome)}</h3>
        ${
          user?.role === "admin" || (user?.permissions || []).includes("projectos.manage")
            ? `<a class="btn btn-outline compact" href="/admin/projectos/${pilar.id}"><i class="bi bi-pencil"></i> Editar</a>`
            : ""
        }
      </div>
      <div class="detail-grid">
        <div>
          <h4>Contexto</h4>
          <p><strong>Area:</strong> ${escapeHtml(pilar.area || "—")}</p>
          <p><strong>Fase:</strong> ${escapeHtml(pilar.fase || "—")}</p>
          <p class="muted pre-wrap">${escapeHtml(pilar.descricao || "")}</p>
        </div>
        <div>
          <h4>Objectivo geral</h4>
          <p class="pre-wrap">${escapeHtml(pilar.obj_geral || "—")}</p>
          ${objs ? `<ul class="list-plain">${objs}</ul>` : ""}
        </div>
        <div>
          <h4>Actividades planeadas</h4>
          <ul class="list-plain">${acts}</ul>
        </div>
        <div>
          <h4>Orcamento</h4>
          <p>${escapeHtml(pilar.orc_moeda || "MZN")} · aprovado: ${pilar.orc_aprovado ?? "—"}</p>
          <ul class="list-plain">${cats}</ul>
        </div>
        <div class="full">
          <h4>Riscos</h4>
          <ul class="list-plain">${risks}</ul>
        </div>
      </div>`;
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
            <span class="status-pill ok">${escapeHtml(p.status || "activo")}</span>
            <span class="status-pill neutro">Prox. ${escapeHtml(p.proxima_avaliacao || "—")}</span>
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
