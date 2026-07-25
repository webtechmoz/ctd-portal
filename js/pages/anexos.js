/** Listagem global de anexos — pesquisa + paginacao no servidor. */
import { api, formatBytes } from "../api.js";
import { bootPage } from "../shell.js";
import { toast } from "../ui.js";

await bootPage({
  page: "anexos",
  title: "Anexos",
  subtitle: "Ficheiros carregados",
});

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

const listEl = document.getElementById("anexos-list");
const controls = document.getElementById("anexos-controls");

let query = "";
let page = 1;
const pageSize = 15;
let debounce = null;

controls.classList.add("list-controls");
controls.innerHTML = `
  <div class="search-field">
    <i class="bi bi-search" aria-hidden="true"></i>
    <input type="search" class="search-input" id="anexos-q" placeholder="Pesquisar ficheiro, projecto, origem, autor..." autocomplete="off" />
  </div>
  <div class="pager" id="anexos-pager" hidden>
    <span class="pager-meta"></span>
    <div class="pager-btns">
      <button type="button" class="pager-btn" data-pager="prev" aria-label="Anterior"><i class="bi bi-chevron-left"></i></button>
      <span class="pager-page"></span>
      <button type="button" class="pager-btn" data-pager="next" aria-label="Seguinte"><i class="bi bi-chevron-right"></i></button>
    </div>
  </div>
`;

const qInput = document.getElementById("anexos-q");
const pagerEl = document.getElementById("anexos-pager");

const params = new URLSearchParams(window.location.search);
if (params.get("q")) {
  query = params.get("q");
  qInput.value = query;
}

qInput.addEventListener("input", () => {
  clearTimeout(debounce);
  debounce = setTimeout(() => {
    query = qInput.value.trim();
    page = 1;
    load();
  }, 280);
});

pagerEl.querySelector('[data-pager="prev"]')?.addEventListener("click", () => {
  if (page > 1) {
    page -= 1;
    load();
  }
});
pagerEl.querySelector('[data-pager="next"]')?.addEventListener("click", () => {
  page += 1;
  load();
});

function sourceLabel(row) {
  return row.source_type_label || row.source_type || "—";
}

async function load() {
  listEl.innerHTML = `<div class="no-data compact"><i class="bi bi-hourglass-split"></i><p>A carregar...</p></div>`;
  try {
    const qs = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (query) qs.set("q", query);
    const data = await api(`/anexos?${qs.toString()}`);
    const rows = data.anexos || [];
    const total = data.total || 0;
    const pages = data.pages || 1;
    page = data.page || page;

    const meta = pagerEl.querySelector(".pager-meta");
    const pageLabel = pagerEl.querySelector(".pager-page");
    if (total) {
      pagerEl.hidden = false;
      const from = (page - 1) * pageSize + 1;
      const to = Math.min(page * pageSize, total);
      meta.textContent = `${from}–${to} de ${total}`;
      pageLabel.textContent = `${page} / ${pages}`;
      pagerEl.querySelector('[data-pager="prev"]').disabled = page <= 1;
      pagerEl.querySelector('[data-pager="next"]').disabled = page >= pages;
    } else {
      pagerEl.hidden = true;
    }

    if (!rows.length) {
      listEl.innerHTML = `<div class="no-data compact"><i class="bi bi-inbox"></i><p>Nenhum anexo encontrado.</p></div>`;
      return;
    }

    listEl.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Ficheiro</th>
            <th>Origem</th>
            <th>Referencia</th>
            <th>Autor</th>
            <th>Data</th>
            <th>Tamanho</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map(
              (r) => `
            <tr>
              <td><strong>${escapeHtml(r.original_name)}</strong></td>
              <td><span class="status-pill neutro">${escapeHtml(sourceLabel(r))}</span></td>
              <td>
                <a href="${escapeHtml(r.source_url || "#")}">${escapeHtml(r.source_label || "—")}</a>
              </td>
              <td>${escapeHtml(r.uploaded_by || "—")}</td>
              <td>${escapeHtml((r.created_at || "").toString().slice(0, 10) || "—")}</td>
              <td>${formatBytes(r.size_bytes)}</td>
              <td>
                <a class="btn btn-outline compact" href="${escapeHtml(r.download_url)}" download>
                  <i class="bi bi-download"></i>
                </a>
              </td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>`;
  } catch (err) {
    toast(err.message || "Erro", "error");
    listEl.innerHTML = `<div class="no-data compact"><p>${escapeHtml(err.message)}</p></div>`;
  }
}

load();
