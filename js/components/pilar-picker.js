/** Custom project picker: styled dropdown + prev/next arrows. */

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

/**
 * @param {HTMLElement} container
 * @param {{ pilares: Array<{id:number,nome:string}>, selectedId?: number, onChange: (id:number)=>void, label?: string }} opts
 */
export function mountPilarPicker(container, { pilares, selectedId, onChange, label = "Projecto" }) {
  if (!container) return { getSelected: () => null, setSelected: () => {} };

  let items = Array.isArray(pilares) ? [...pilares] : [];
  let currentId =
    selectedId && items.some((p) => p.id === selectedId)
      ? selectedId
      : items[0]?.id ?? null;

  container.classList.add("pilar-picker");
  container.innerHTML = `
    <button type="button" class="pilar-picker-nav" data-dir="-1" aria-label="Projecto anterior" title="Anterior">
      <i class="bi bi-chevron-left"></i>
    </button>
    <div class="pilar-dd" data-dd>
      <button type="button" class="pilar-dd-trigger" aria-haspopup="listbox" aria-expanded="false">
        <span class="pilar-dd-label">${escapeHtml(label)}</span>
        <span class="pilar-dd-value"></span>
        <i class="bi bi-chevron-down"></i>
      </button>
      <div class="pilar-dd-menu" role="listbox" hidden></div>
    </div>
    <button type="button" class="pilar-picker-nav" data-dir="1" aria-label="Proximo projecto" title="Seguinte">
      <i class="bi bi-chevron-right"></i>
    </button>
  `;

  const valueEl = container.querySelector(".pilar-dd-value");
  const trigger = container.querySelector(".pilar-dd-trigger");
  const menu = container.querySelector(".pilar-dd-menu");
  const dd = container.querySelector("[data-dd]");

  function currentIndex() {
    return items.findIndex((p) => p.id === currentId);
  }

  function currentItem() {
    return items.find((p) => p.id === currentId) || null;
  }

  function paint() {
    const item = currentItem();
    valueEl.textContent = item ? item.nome : "Sem projectos";
    trigger.disabled = !items.length;
    container.querySelectorAll(".pilar-picker-nav").forEach((btn) => {
      btn.disabled = items.length < 2;
    });
    menu.innerHTML = items
      .map(
        (p) => `
      <button type="button" class="pilar-dd-option ${p.id === currentId ? "active" : ""}" role="option" data-id="${p.id}" aria-selected="${p.id === currentId}">
        ${escapeHtml(p.nome)}
      </button>`
      )
      .join("");
  }

  function closeMenu() {
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    dd.classList.remove("open");
  }

  function openMenu() {
    if (!items.length) return;
    menu.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    dd.classList.add("open");
  }

  function setSelected(id, { silent = false } = {}) {
    if (!items.some((p) => p.id === id)) return;
    if (id === currentId && !silent) return;
    currentId = id;
    paint();
    closeMenu();
    if (!silent) onChange?.(currentId);
  }

  function step(dir) {
    if (items.length < 2) return;
    let idx = currentIndex();
    if (idx < 0) idx = 0;
    const next = (idx + dir + items.length) % items.length;
    setSelected(items[next].id);
  }

  container.addEventListener("click", (e) => {
    const nav = e.target.closest(".pilar-picker-nav");
    if (nav) {
      e.preventDefault();
      step(Number(nav.dataset.dir));
      return;
    }
    const opt = e.target.closest(".pilar-dd-option");
    if (opt) {
      e.preventDefault();
      setSelected(Number(opt.dataset.id));
      return;
    }
    if (e.target.closest(".pilar-dd-trigger")) {
      e.preventDefault();
      if (menu.hidden) openMenu();
      else closeMenu();
    }
  });

  document.addEventListener("click", (e) => {
    if (!container.contains(e.target)) closeMenu();
  });

  paint();
  return {
    getSelected: () => currentId,
    setSelected: (id) => setSelected(id, { silent: true }),
    update(list, id) {
      items = Array.isArray(list) ? [...list] : [];
      if (id != null && items.some((p) => p.id === id)) currentId = id;
      else if (!items.some((p) => p.id === currentId)) currentId = items[0]?.id ?? null;
      paint();
    },
  };
}
