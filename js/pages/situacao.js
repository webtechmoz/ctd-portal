/** Ponto de situacao — cards com pesquisa e paginacao. */
import { api } from "../api.js";
import { filterByQuery, mountSearchPager, paginate } from "../components/list-kit.js";
import { bootPage } from "../shell.js";
import { setLoading, toast } from "../ui.js";

await bootPage({
  page: "situacao",
  title: "Ponto de situacao",
  subtitle: "Prazos e janelas de avaliacao",
});

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function daysUntil(iso) {
  if (!iso) return null;
  const d = new Date(iso + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((d - today) / 86400000);
}

function situacaoMeta(p) {
  const days = daysUntil(p.proxima_avaliacao);
  let badge = "neutro";
  let label = "Sem data agendada";
  if (days !== null) {
    if (days < 0) {
      badge = "atraso";
      label = `Atrasado ${Math.abs(days)}d`;
    } else if (days === 0) {
      badge = "hoje";
      label = "Hoje";
    } else {
      badge = days <= 7 ? "breve" : "ok";
      label = `em ${days}d`;
    }
  }
  return { days, badge, label };
}

const el = document.getElementById("situacao-list");
let allItems = [];

const pager = mountSearchPager(document.getElementById("situacao-controls"), {
  pageSize: 9,
  placeholder: "Pesquisar projecto, fase, prazo, situacao...",
  onChange: render,
});

function render() {
  const filtered = filterByQuery(allItems, pager.query, (p) => {
    const meta = situacaoMeta(p);
    return [p.nome, p.area, p.fase, p.status, p.proxima_avaliacao, meta.label, meta.badge];
  });
  const page = paginate(filtered, pager.page, pager.pageSize);
  pager.setMeta(page);

  if (!page.total) {
    el.innerHTML = `<div class="no-data compact"><i class="bi bi-inbox"></i><p>Sem resultados.</p></div>`;
    return;
  }

  el.innerHTML = page.items
    .map((p) => {
      const meta = situacaoMeta(p);
      return `
        <a class="info-card" href="/avaliacao?pilar=${p.id}">
          <div>
            <strong>${escapeHtml(p.nome)}</strong>
            <span>${escapeHtml(p.fase || "—")} · ${escapeHtml(p.proxima_avaliacao || "—")}</span>
            <div class="card-meta"><span class="status-pill ${meta.badge}">${escapeHtml(meta.label)}</span></div>
          </div>
          <div class="card-foot"><span>Avaliar</span><i class="bi bi-arrow-right"></i></div>
        </a>`;
    })
    .join("");
}

setLoading(el);
try {
  const { pilares } = await api("/pilares");
  allItems = [...(pilares || [])].sort((a, b) => {
    const da = daysUntil(a.proxima_avaliacao) ?? 9999;
    const db = daysUntil(b.proxima_avaliacao) ?? 9999;
    return da - db;
  });
  render();
} catch (err) {
  toast(err.message || "Erro", "error");
  el.innerHTML = `<div class="no-data compact"><p>${escapeHtml(err.message)}</p></div>`;
}
