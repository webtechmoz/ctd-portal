/** Home — dashboard global. */
import { api } from "../api.js";
import { filterByQuery, mountSearchPager, paginate } from "../components/list-kit.js";
import { bootPage } from "../shell.js";
import { setLoading, toast } from "../ui.js";

await bootPage({
  page: "home",
  title: "Dashboard",
  subtitle: "Visao global do portefolio CTD",
});

const homeList = document.getElementById("home-list");
setLoading(homeList, "A carregar projectos...");

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function money(n) {
  return Number(n || 0).toLocaleString("pt-MZ", { maximumFractionDigits: 0 });
}

const COLORS = {
  green: "#3a7d2c",
  greenSoft: "rgba(58, 125, 44, 0.65)",
  accent: "#f5a623",
  blue: "#1976d2",
  red: "#e74c3c",
  gray: "#90a4ae",
};

let allItems = [];

const pager = mountSearchPager(document.getElementById("home-controls"), {
  pageSize: 9,
  placeholder: "Pesquisar projecto, area, fase, prazo...",
  onChange: renderHomeList,
});

function cardMeta(p) {
  let badge = "neutro";
  let label = "Sem data";
  if (p.dias !== null && p.dias !== undefined) {
    if (p.dias < 0) {
      badge = "atraso";
      label = `${Math.abs(p.dias)}d atraso`;
    } else if (p.dias === 0) {
      badge = "hoje";
      label = "Hoje";
    } else {
      badge = p.dias <= 7 ? "breve" : "ok";
      label = `em ${p.dias}d`;
    }
  }
  return { badge, label };
}

function renderHomeList() {
  const filtered = filterByQuery(allItems, pager.query, (p) => {
    const meta = cardMeta(p);
    return [
      p.nome,
      p.area,
      p.fase,
      p.situacao,
      meta.label,
      p.progresso,
      p.orc_aprovado,
      p.proxima_avaliacao,
    ];
  });
  const page = paginate(filtered, pager.page, pager.pageSize);
  pager.setMeta(page);

  if (!page.total) {
    homeList.innerHTML = `<div class="no-data compact"><i class="bi bi-inbox"></i><p>Nenhum projecto.</p></div>`;
    return;
  }

  homeList.innerHTML = page.items
    .map((p) => {
      const meta = cardMeta(p);
      return `
        <a class="info-card" href="/dashboard?pilar=${p.id}">
          <div>
            <strong>${escapeHtml(p.nome)}</strong>
            <span>${escapeHtml(p.area || "—")} · ${escapeHtml(p.fase || "—")}</span>
            <div class="card-meta">
              <span class="status-pill ${meta.badge}">${meta.label}</span>
              <span class="status-pill ok">${Number(p.progresso || 0).toFixed(0)}% prog.</span>
            </div>
          </div>
          <div class="card-foot">
            <span>Orc. ${money(p.orc_aprovado)} ${escapeHtml(p.orc_moeda || "MZN")}</span>
            <i class="bi bi-chevron-right"></i>
          </div>
        </a>`;
    })
    .join("");
}

try {
  const data = await api("/reports/overview");
  const r = data.resumo || {};
  const list = data.pilares || [];

  document.getElementById("kpi-projectos").textContent = String(r.projectos ?? 0);
  document.getElementById("kpi-orc-total").textContent = money(r.orcamento_aprovado_total);
  document.getElementById("kpi-orc-pct").textContent = `${Number(r.orcamento_pct_global || 0).toFixed(0)}%`;
  document.getElementById("kpi-atraso").textContent = String(r.atraso ?? 0);

  if (window.Chart) {
    new window.Chart(document.getElementById("chart-situacao"), {
      type: "doughnut",
      data: {
        labels: ["Em dia", "Proximos 7 dias", "Em atraso", "Sem data"],
        datasets: [
          {
            data: [r.ok || 0, r.breve || 0, r.atraso || 0, r.sem_data || 0],
            backgroundColor: [COLORS.green, COLORS.accent, COLORS.red, COLORS.gray],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        cutout: "62%",
      },
    });

    new window.Chart(document.getElementById("chart-progresso"), {
      type: "bar",
      data: {
        labels: list.map((p) => p.nome),
        datasets: [
          {
            label: "Progresso %",
            data: list.map((p) => p.progresso || 0),
            backgroundColor: COLORS.greenSoft,
            borderRadius: 6,
          },
          {
            label: "Orcamento %",
            data: list.map((p) => p.orcamento_pct || 0),
            backgroundColor: "rgba(245, 166, 35, 0.7)",
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: true, max: 100, ticks: { callback: (v) => `${v}%` } },
        },
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  allItems = [...list].sort((a, b) => (a.dias ?? 9999) - (b.dias ?? 9999));
  renderHomeList();
} catch (err) {
  toast(err.message || "Falha ao carregar", "error");
  setLoading(homeList, err.message || "Erro ao carregar");
}
