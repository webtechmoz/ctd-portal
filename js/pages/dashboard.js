/** Dashboard page with charts. */
import { api } from "../api.js";
import { mountPilarPicker } from "../components/pilar-picker.js";
import { bootPage } from "../shell.js";
import { setLoading, toast } from "../ui.js";

await bootPage({
  page: "resultados",
  title: "Resultados",
  subtitle: "KPIs e graficos da ultima avaliacao",
});

const pickerHost = document.getElementById("pilar-picker");
const content = document.getElementById("dash-content");
let charts = [];
let picker = null;

function pct(n) {
  return `${Number(n || 0).toFixed(0)}%`;
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function destroyCharts() {
  charts.forEach((c) => c.destroy());
  charts = [];
}

function renderEmpty(message) {
  destroyCharts();
  content.innerHTML = `
    <div class="no-data">
      <i class="bi bi-inbox"></i>
      <p>${message}</p>
    </div>`;
}

function renderDashboard(data) {
  destroyCharts();
  const r = data.resumo || {};
  if (!data.tem_avaliacao) {
    content.innerHTML = `
      <div class="no-data">
        <i class="bi bi-clipboard2"></i>
        <p>Ainda nao ha avaliacao para <strong>${escapeHtml(data.pilar.nome)}</strong>.</p>
        <p class="empty-hint" style="margin-top:8px">
          <a class="btn btn-primary" href="/avaliacao?pilar=${data.pilar.id}">Nova avaliacao</a>
        </p>
      </div>`;
    return;
  }

  const actividades = (data.actividades || [])
    .map(
      (a) => `
      <div class="act-row">
        <strong style="flex:1">${escapeHtml(a.nome)}</strong>
        <span class="badge ${a.estado}">${a.estado.replace("_", " ")}</span>
        <span>${a.pct_conclusao}%</span>
        <div class="progress-bar-wrap" style="width:100%">
          <div class="progress-bar" style="width:${a.pct_conclusao}%"></div>
        </div>
      </div>`
    )
    .join("") || `<p class="empty-hint">Sem actividades nesta avaliacao</p>`;

  const orcamentos = (data.orcamentos || [])
    .map((o) => {
      const al = Number(o.valor_alocado || 0);
      const ex = Number(o.valor_executado || 0);
      const p = al ? Math.min(100, (ex / al) * 100) : 0;
      return `
        <div class="orc-row">
          <strong style="flex:1">${escapeHtml(o.categoria)}</strong>
          <span>${ex.toLocaleString("pt-MZ")} / ${al.toLocaleString("pt-MZ")}</span>
          <div class="progress-bar-wrap" style="width:100%">
            <div class="progress-bar" style="width:${p}%"></div>
          </div>
        </div>`;
    })
    .join("") || `<p class="empty-hint">Sem dados de orcamento</p>`;

  const riscos = (data.riscos || [])
    .map(
      (r) => `
      <div class="risk-row">
        <div style="flex:1">${escapeHtml(r.descricao)}</div>
        <span class="badge ${r.probabilidade}">${r.probabilidade}</span>
        <span class="badge ${r.impacto}">${r.impacto}</span>
      </div>`
    )
    .join("") || `<p class="empty-hint">Sem riscos registados</p>`;

  content.innerHTML = `
    <div class="kpi-row">
      <div class="kpi-card"><div class="label">Progresso global</div><div class="value">${pct(r.progresso)}</div></div>
      <div class="kpi-card accent"><div class="label">Execucao orcamental</div><div class="value">${pct(r.orcamento_pct)}</div></div>
      <div class="kpi-card blue"><div class="label">Actividades</div><div class="value">${r.actividades_concluidas || 0}/${r.actividades_total || 0}</div></div>
      <div class="kpi-card red"><div class="label">Riscos altos</div><div class="value">${r.riscos_altos || 0}</div></div>
    </div>
    <div class="charts-row">
      <div class="chart-card">
        <h4><i class="bi bi-pie-chart"></i> Estado das actividades</h4>
        <div class="chart-wrap"><canvas id="chart-acts"></canvas></div>
      </div>
      <div class="chart-card">
        <h4><i class="bi bi-cash-stack"></i> Orcamento por rubrica</h4>
        <div class="chart-wrap"><canvas id="chart-orc"></canvas></div>
      </div>
    </div>
    <div class="dash-grid">
      <div class="dash-card">
        <h4><i class="bi bi-chat-left-text"></i> Avaliacao geral</h4>
        <p style="font-size:0.9rem;line-height:1.5;white-space:pre-wrap">${escapeHtml(data.estado_geral || "—")}</p>
        <p class="empty-hint" style="margin-top:10px">Submetido: ${data.data_sub || "—"}</p>
      </div>
      <div class="dash-card">
        <h4><i class="bi bi-exclamation-octagon"></i> Riscos</h4>
        ${riscos}
      </div>
      <div class="dash-card full">
        <h4><i class="bi bi-list-task"></i> Actividades</h4>
        ${actividades}
      </div>
      <div class="dash-card full">
        <h4><i class="bi bi-cash-stack"></i> Orcamento</h4>
        ${orcamentos}
      </div>
    </div>`;

  if (window.Chart) {
    charts.push(
      new window.Chart(document.getElementById("chart-acts"), {
        type: "doughnut",
        data: {
          labels: ["Concluidas", "Em progresso", "Pendentes"],
          datasets: [
            {
              data: [
                r.actividades_concluidas || 0,
                r.actividades_em_progresso || 0,
                r.actividades_pendentes || 0,
              ],
              backgroundColor: ["#3a7d2c", "#1976d2", "#f5a623"],
              borderWidth: 0,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "bottom" } },
          cutout: "60%",
        },
      })
    );

    const cats = data.orcamentos || [];
    charts.push(
      new window.Chart(document.getElementById("chart-orc"), {
        type: "bar",
        data: {
          labels: cats.map((c) => c.categoria),
          datasets: [
            {
              label: "Alocado",
              data: cats.map((c) => Number(c.valor_alocado || 0)),
              backgroundColor: "rgba(25, 118, 210, 0.55)",
              borderRadius: 6,
            },
            {
              label: "Executado",
              data: cats.map((c) => Number(c.valor_executado || 0)),
              backgroundColor: "rgba(58, 125, 44, 0.7)",
              borderRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "bottom" } },
        },
      })
    );
  }
}

async function loadDashboard(id) {
  const url = new URL(window.location.href);
  url.searchParams.set("pilar", String(id));
  window.history.replaceState({}, "", url);
  setLoading(content, "A carregar resultados...");
  try {
    const data = await api(`/pilares/${id}/dashboard`);
    renderDashboard(data);
  } catch (err) {
    toast(err.message || "Falha ao carregar dashboard", "error");
    renderEmpty(err.message || "Erro ao carregar");
  }
}

async function init() {
  setLoading(content, "A carregar pilares...");
  try {
    const { pilares } = await api("/pilares");
    if (!pilares?.length) {
      renderEmpty("Nenhum pilar activo.");
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const fromQuery = Number(params.get("pilar"));
    const startId = pilares.some((p) => p.id === fromQuery) ? fromQuery : pilares[0].id;
    picker = mountPilarPicker(pickerHost, {
      pilares,
      selectedId: startId,
      onChange: (id) => loadDashboard(id),
    });
    await loadDashboard(startId);
  } catch (err) {
    toast(err.message || "Falha ao listar pilares", "error");
    renderEmpty(err.message || "Erro");
  }
}

init();
