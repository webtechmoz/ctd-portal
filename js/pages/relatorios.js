/** Relatorios de avaliacao — tabela + export Excel. */
import { api, apiDownload } from "../api.js";
import { bindDatePicker } from "../components/dates.js";
import { enhanceSelect } from "../components/styled-select.js";
import { filterByQuery, mountSearchPager, paginate } from "../components/list-kit.js";
import { bootPage } from "../shell.js";
import { setLoading, toast } from "../ui.js";

await bootPage({
  page: "relatorios",
  title: "Relatorios",
  subtitle: "Avaliacoes por periodo e estado",
});

const listEl = document.getElementById("report-list");
const countEl = document.getElementById("report-count");
const pilarSel = document.getElementById("filter-pilar");
const statusSel = document.getElementById("filter-status");
const fromEl = document.getElementById("filter-from");
const toEl = document.getElementById("filter-to");

bindDatePicker(fromEl);
bindDatePicker(toEl);

let allItems = [];

const pager = mountSearchPager(document.getElementById("report-controls"), {
  pageSize: 15,
  placeholder: "Pesquisar projecto, autor, status...",
  onChange: renderList,
});

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function fmtDate(iso) {
  if (!iso) return "—";
  const raw = String(iso).slice(0, 10);
  const [y, m, d] = raw.split("-");
  if (!y || !m || !d) return raw;
  return `${d}/${m}/${y}`;
}

function queryPath() {
  const q = new URLSearchParams();
  if (pilarSel.value) q.set("pilar_id", pilarSel.value);
  if (statusSel.value) q.set("status", statusSel.value);
  if (fromEl.value) q.set("from", fromEl.value);
  if (toEl.value) q.set("to", toEl.value);
  const s = q.toString();
  return s ? `?${s}` : "";
}

function statusPill(st) {
  const map = { validada: "ok", submetida: "warn", reaberta: "breve" };
  return `<span class="status-pill ${map[st] || "neutro"}">${escapeHtml(st || "—")}</span>`;
}

function renderList() {
  const filtered = filterByQuery(allItems, pager.query, (r) => [
    r.pilar_nome,
    r.autor,
    r.status,
    r.estado_geral,
    r.data_sub,
  ]);
  const page = paginate(filtered, pager.page, pager.pageSize);
  pager.setMeta(page);
  if (countEl) countEl.textContent = String(page.total);
  if (!page.total) {
    listEl.innerHTML = `<div class="no-data compact"><i class="bi bi-inbox"></i><p>Sem resultados.</p></div>`;
    return;
  }
  listEl.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Data</th>
          <th>Projecto</th>
          <th>Progresso</th>
          <th>Orc. %</th>
          <th>Riscos altos</th>
          <th>Status</th>
          <th>Autor</th>
        </tr>
      </thead>
      <tbody>
        ${page.items
          .map(
            (r) => `
          <tr>
            <td>${escapeHtml(fmtDate(r.data_sub))}</td>
            <td><strong>${escapeHtml(r.pilar_nome)}</strong></td>
            <td>
              <div class="report-meter">
                <span style="width:${Math.min(100, Number(r.progresso || 0))}%"></span>
              </div>
              <small>${Number(r.progresso || 0).toFixed(0)}%</small>
            </td>
            <td>${Number(r.orcamento_pct || 0).toFixed(0)}%</td>
            <td>${Number(r.riscos_altos || 0)}</td>
            <td>${statusPill(r.status)}</td>
            <td>${escapeHtml(r.autor || "—")}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>`;
}

async function load() {
  setLoading(listEl, "A carregar...");
  try {
    const data = await api(`/reports/avaliacoes${queryPath()}`);
    allItems = data.avaliacoes || [];
    renderList();
  } catch (err) {
    toast(err.message || "Erro", "error");
    listEl.innerHTML = `<div class="no-data compact"><p>${escapeHtml(err.message)}</p></div>`;
  }
}

document.getElementById("btn-apply").addEventListener("click", () => {
  pager.page = 1;
  load();
});

document.getElementById("btn-export").addEventListener("click", async () => {
  try {
    await apiDownload(`/reports/avaliacoes/export.xlsx${queryPath()}`, "relatorio-avaliacoes.xlsx");
    toast("Exportacao iniciada.", "success");
  } catch (err) {
    toast(err.message || "Erro ao exportar", "error");
  }
});

try {
  const { pilares } = await api("/pilares");
  for (const p of pilares || []) {
    const opt = document.createElement("option");
    opt.value = String(p.id);
    opt.textContent = p.nome;
    pilarSel.appendChild(opt);
  }
  enhanceSelect(pilarSel);
  enhanceSelect(statusSel);
} catch {
  /* ignore */
}

await load();
