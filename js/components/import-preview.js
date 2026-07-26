/** Preview modal for project Excel import. */
import { apiForm } from "../api.js";
import { closeModal, openModal } from "./modal.js";
import { toast } from "../ui.js";

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function ensureModal() {
  let el = document.getElementById("modal-import-preview");
  if (el) return el;
  el = document.createElement("div");
  el.className = "modal-backdrop";
  el.id = "modal-import-preview";
  el.hidden = true;
  el.innerHTML = `
    <div class="modal-card wide" role="dialog" aria-modal="true">
      <div class="modal-head">
        <h3>Pré-visualização da importação</h3>
        <button type="button" class="modal-close" data-close-modal aria-label="Fechar"><i class="bi bi-x-lg"></i></button>
      </div>
      <div class="modal-body">
        <p class="panel-hint" id="import-preview-summary"></p>
        <div id="import-preview-errors" class="import-errors" hidden></div>
        <div id="import-preview-table" class="import-preview-scroll"></div>
      </div>
      <div class="modal-foot">
        <button type="button" class="btn btn-primary compact" id="btn-import-confirm" disabled>Confirmar importação</button>
        <button type="button" class="btn btn-outline compact" data-close-modal>Cancelar</button>
      </div>
    </div>`;
  document.body.appendChild(el);
  el.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal(el));
  });
  el.addEventListener("click", (e) => {
    if (e.target === el) closeModal(el);
  });
  return el;
}

export async function runProjectImport(file, { onSuccess } = {}) {
  if (!file) return;
  const modal = ensureModal();
  const summary = modal.querySelector("#import-preview-summary");
  const errBox = modal.querySelector("#import-preview-errors");
  const table = modal.querySelector("#import-preview-table");
  const confirmBtn = modal.querySelector("#btn-import-confirm");

  summary.textContent = "A validar ficheiro...";
  errBox.hidden = true;
  errBox.innerHTML = "";
  table.innerHTML = "";
  confirmBtn.disabled = true;
  openModal(modal);

  const fd = new FormData();
  fd.append("file", file);
  let dry;
  try {
    dry = await apiForm("/pilares/import?dry_run=1", fd);
  } catch (err) {
    closeModal(modal);
    toast(err.message || "Erro na validação", "error");
    return;
  }

  const errs = dry.errors || [];
  const preview = dry.preview || [];
  summary.textContent = dry.ok
    ? `Pronto: ${dry.created || 0} novos, ${dry.updated || 0} actualizações.`
    : `Encontrados ${errs.length} erro(s) que bloqueiam a importação.`;

  if (errs.length) {
    errBox.hidden = false;
    errBox.innerHTML = `<ul>${errs
      .slice(0, 40)
      .map((e) => `<li>${escapeHtml(e)}</li>`)
      .join("")}${errs.length > 40 ? `<li>… +${errs.length - 40} erros</li>` : ""}</ul>`;
  }

  if (!preview.length) {
    table.innerHTML = `<div class="no-data compact"><p>Sem linhas de projecto no ficheiro.</p></div>`;
  } else {
    table.innerHTML = `
      <table class="data-table compact">
        <thead>
          <tr>
            <th>Linha</th>
            <th>Projecto</th>
            <th>Acção</th>
            <th>Área</th>
            <th>Fase</th>
            <th>Nested</th>
            <th>Erros</th>
          </tr>
        </thead>
        <tbody>
          ${preview
            .map((p) => {
              const actionCls =
                p.action === "create" ? "ok" : p.action === "update" ? "warn" : "atraso";
              const nested = `${p.actividades || 0} act · ${p.rubricas || 0} rub · ${p.riscos || 0} risc`;
              const rowErrs = (p.errors || []).join("; ") || "—";
              return `<tr class="${p.errors?.length ? "row-error" : ""}">
                <td>${p.linha || "—"}</td>
                <td><strong>${escapeHtml(p.nome)}</strong></td>
                <td><span class="status-pill ${actionCls}">${escapeHtml(p.action)}</span></td>
                <td>${escapeHtml(p.area || "—")}</td>
                <td>${escapeHtml(p.fase || "—")}</td>
                <td>${escapeHtml(nested)}</td>
                <td class="import-err-cell">${escapeHtml(rowErrs)}</td>
              </tr>`;
            })
            .join("")}
        </tbody>
      </table>`;
  }

  confirmBtn.disabled = !dry.ok;
  confirmBtn.onclick = async () => {
    if (!dry.ok) return;
    confirmBtn.disabled = true;
    try {
      const fd2 = new FormData();
      fd2.append("file", file);
      const result = await apiForm("/pilares/import", fd2);
      closeModal(modal);
      toast(
        `Importação: ${result.created || 0} criados, ${result.updated || 0} actualizados.`,
        result.ok ? "success" : "error"
      );
      if (result.ok && onSuccess) await onSuccess(result);
    } catch (err) {
      toast(err.message || "Erro na importação", "error");
      confirmBtn.disabled = false;
    }
  };
}
