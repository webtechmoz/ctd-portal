/** Replace native <select> with a styled dropdown (hidden native select stays in sync). */

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function closeAllMenus(except) {
  document.querySelectorAll(".styled-select.open").forEach((el) => {
    if (el === except) return;
    el.classList.remove("open");
    const m = el._styledMenu;
    if (m) {
      m.hidden = true;
      if (m.parentNode !== el) el.appendChild(m);
      clearMenuInline(m);
    }
  });
}

function clearMenuInline(menu) {
  [
    "position",
    "top",
    "bottom",
    "left",
    "right",
    "width",
    "minWidth",
    "maxWidth",
    "maxHeight",
    "zIndex",
    "overflowY",
    "overscrollBehavior",
    "boxSizing",
  ].forEach((k) => {
    menu.style[k] = "";
  });
}

/** Close every open styled-select (e.g. when a dialog closes). */
export function closeStyledSelects() {
  closeAllMenus(null);
}

/**
 * @param {HTMLSelectElement} select
 * @param {{ className?: string }} [opts]
 */
export function enhanceSelect(select, opts = {}) {
  if (!select || select.dataset.enhanced === "1") return;
  select.dataset.enhanced = "1";
  select.classList.add("sr-only-select");
  select.setAttribute("tabindex", "-1");

  const wrap = document.createElement("div");
  wrap.className = `styled-select ${opts.className || ""}`.trim();
  select.parentNode.insertBefore(wrap, select);
  wrap.appendChild(select);

  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "styled-select-trigger";
  trigger.innerHTML = `<span class="styled-select-value"></span><i class="bi bi-chevron-down" aria-hidden="true"></i>`;
  const menu = document.createElement("div");
  menu.className = "styled-select-menu";
  menu.hidden = true;
  menu.tabIndex = -1;
  menu.setAttribute("role", "listbox");
  wrap.appendChild(trigger);
  wrap.appendChild(menu);
  wrap._styledMenu = menu;

  const valueEl = trigger.querySelector(".styled-select-value");
  let highlightIndex = -1;

  function optionButtons() {
    return [...menu.querySelectorAll(".styled-select-option:not(:disabled)")];
  }

  function paint() {
    const opt = select.selectedOptions[0];
    valueEl.textContent = opt ? opt.textContent : "—";
    menu.innerHTML = [...select.options]
      .map(
        (o) => `
      <button type="button" class="styled-select-option ${o.selected ? "active" : ""}" data-value="${escapeHtml(o.value)}" ${o.disabled ? "disabled" : ""} role="option" aria-selected="${o.selected ? "true" : "false"}" tabindex="-1">
        ${escapeHtml(o.textContent)}
      </button>`
      )
      .join("");
    const opts = optionButtons();
    highlightIndex = opts.findIndex((b) => b.classList.contains("active"));
    if (highlightIndex < 0) highlightIndex = opts.length ? 0 : -1;
  }

  function setHighlight(index) {
    const opts = optionButtons();
    if (!opts.length) return;
    highlightIndex = ((index % opts.length) + opts.length) % opts.length;
    opts.forEach((b, i) => {
      const on = i === highlightIndex;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    opts[highlightIndex]?.scrollIntoView({ block: "nearest" });
  }

  function positionMenu() {
    const rect = trigger.getBoundingClientRect();
    const width = Math.max(0, rect.width);
    const maxH = 200;
    const gap = 4;
    const pad = 8;
    const spaceBelow = window.innerHeight - rect.bottom - pad;
    const spaceAbove = rect.top - pad;
    const openUp = spaceBelow < 120 && spaceAbove > spaceBelow;
    const avail = Math.max(96, openUp ? spaceAbove : spaceBelow);

    let left = rect.left;
    if (left + width > window.innerWidth - pad) {
      left = Math.max(pad, window.innerWidth - pad - width);
    }
    if (left < pad) left = pad;

    menu.style.position = "fixed";
    menu.style.boxSizing = "border-box";
    menu.style.left = `${left}px`;
    menu.style.width = `${width}px`;
    menu.style.minWidth = `${width}px`;
    menu.style.maxWidth = `${width}px`;
    menu.style.maxHeight = `${Math.min(maxH, avail)}px`;
    menu.style.zIndex = "600";
    menu.style.overflowY = "auto";
    menu.style.overscrollBehavior = "contain";
    if (openUp) {
      menu.style.top = "auto";
      menu.style.bottom = `${window.innerHeight - rect.top + gap}px`;
    } else {
      menu.style.bottom = "auto";
      menu.style.top = `${rect.bottom + gap}px`;
    }
  }

  function close() {
    if (menu.hidden) return;
    menu.hidden = true;
    wrap.classList.remove("open");
    trigger.setAttribute("aria-expanded", "false");
    if (menu.parentNode !== wrap) wrap.appendChild(menu);
    clearMenuInline(menu);
  }

  function open() {
    closeAllMenus(wrap);
    paint();
    document.body.appendChild(menu);
    menu.hidden = false;
    wrap.classList.add("open");
    trigger.setAttribute("aria-expanded", "true");
    positionMenu();
    setHighlight(highlightIndex < 0 ? 0 : highlightIndex);
  }

  function pickValue(value) {
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    paint();
    close();
    trigger.focus();
  }

  function pickHighlighted() {
    const opts = optionButtons();
    if (opts[highlightIndex]) pickValue(opts[highlightIndex].dataset.value);
  }

  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");

  trigger.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (menu.hidden) open();
    else close();
  });

  // Focus stays on the trigger — handle keys here while open
  trigger.addEventListener("keydown", (e) => {
    const openKeys = ["ArrowDown", "ArrowUp", "Enter", " "];
    if (menu.hidden) {
      if (openKeys.includes(e.key)) {
        e.preventDefault();
        e.stopPropagation();
        open();
        if (e.key === "ArrowUp") setHighlight(optionButtons().length - 1);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      e.stopPropagation();
      setHighlight(highlightIndex + 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      e.stopPropagation();
      setHighlight(highlightIndex - 1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      e.stopPropagation();
      pickHighlighted();
    } else if (e.key === " ") {
      e.preventDefault();
      e.stopPropagation();
      pickHighlighted();
    } else if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      close();
    } else if (e.key === "Tab") {
      close();
    }
  });

  menu.addEventListener("mousedown", (e) => {
    // Prevent trigger blur/outside-click races before click fires
    e.preventDefault();
  });

  menu.addEventListener("click", (e) => {
    const btn = e.target.closest(".styled-select-option");
    if (!btn || btn.disabled) return;
    e.preventDefault();
    e.stopPropagation();
    pickValue(btn.dataset.value);
  });

  menu.addEventListener(
    "wheel",
    (e) => {
      e.stopPropagation();
    },
    { passive: true }
  );

  document.addEventListener("click", (e) => {
    if (!wrap.classList.contains("open")) return;
    if (wrap.contains(e.target) || menu.contains(e.target)) return;
    close();
  });

  window.addEventListener(
    "scroll",
    (e) => {
      if (!wrap.classList.contains("open")) return;
      const t = e.target;
      if (t === menu || (t instanceof Node && menu.contains(t))) return;
      close();
    },
    true
  );
  window.addEventListener("resize", () => {
    if (wrap.classList.contains("open")) close();
  });

  paint();
  return { refresh: paint, close };
}
