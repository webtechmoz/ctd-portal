/** Replace native <select> look with a styled dropdown (keeps a hidden native select in sync). */

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
    }
  });
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
  trigger.innerHTML = `<span class="styled-select-value"></span><i class="bi bi-chevron-down"></i>`;
  const menu = document.createElement("div");
  menu.className = "styled-select-menu";
  menu.hidden = true;
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
      <button type="button" class="styled-select-option ${o.selected ? "active" : ""}" data-value="${escapeHtml(o.value)}" ${o.disabled ? "disabled" : ""} role="option" aria-selected="${o.selected ? "true" : "false"}">
        ${escapeHtml(o.textContent)}
      </button>`
      )
      .join("");
    highlightIndex = optionButtons().findIndex((b) => b.classList.contains("active"));
  }

  function setHighlight(index) {
    const opts = optionButtons();
    if (!opts.length) return;
    highlightIndex = Math.max(0, Math.min(index, opts.length - 1));
    opts.forEach((b, i) => b.classList.toggle("active", i === highlightIndex));
    opts[highlightIndex]?.scrollIntoView({ block: "nearest" });
  }

  function positionMenu() {
    const rect = trigger.getBoundingClientRect();
    const maxH = 220;
    const spaceBelow = window.innerHeight - rect.bottom - 8;
    const spaceAbove = rect.top - 8;
    const openUp = spaceBelow < Math.min(maxH, 140) && spaceAbove > spaceBelow;
    const avail = Math.max(120, openUp ? spaceAbove : spaceBelow);
    menu.style.position = "fixed";
    menu.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8))}px`;
    menu.style.width = `${Math.max(rect.width, 120)}px`;
    menu.style.maxHeight = `${Math.min(maxH, avail)}px`;
    menu.style.zIndex = "600";
    menu.style.overflowY = "auto";
    menu.style.overscrollBehavior = "contain";
    if (openUp) {
      menu.style.top = "auto";
      menu.style.bottom = `${window.innerHeight - rect.top + 4}px`;
    } else {
      menu.style.bottom = "auto";
      menu.style.top = `${rect.bottom + 4}px`;
    }
  }

  function close() {
    menu.hidden = true;
    wrap.classList.remove("open");
    trigger.setAttribute("aria-expanded", "false");
    if (menu.parentNode !== wrap) wrap.appendChild(menu);
    menu.style.position = "";
    menu.style.top = "";
    menu.style.bottom = "";
    menu.style.left = "";
    menu.style.width = "";
    menu.style.maxHeight = "";
    menu.style.zIndex = "";
    menu.style.overflowY = "";
    menu.style.overscrollBehavior = "";
  }

  function open() {
    closeAllMenus(wrap);
    document.body.appendChild(menu);
    menu.hidden = false;
    wrap.classList.add("open");
    trigger.setAttribute("aria-expanded", "true");
    positionMenu();
    setHighlight(Math.max(0, highlightIndex));
  }

  function pickValue(value) {
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    paint();
    close();
    trigger.focus();
  }

  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");

  trigger.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (menu.hidden) open();
    else close();
  });

  trigger.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (menu.hidden) open();
      else if (e.key === "ArrowDown") setHighlight(highlightIndex + 1);
    } else if (e.key === "Escape") {
      close();
    }
  });

  menu.addEventListener("click", (e) => {
    const btn = e.target.closest(".styled-select-option");
    if (!btn || btn.disabled) return;
    pickValue(btn.dataset.value);
  });

  menu.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight(highlightIndex + 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight(highlightIndex - 1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const opts = optionButtons();
      if (opts[highlightIndex]) pickValue(opts[highlightIndex].dataset.value);
    } else if (e.key === "Escape") {
      e.preventDefault();
      close();
      trigger.focus();
    }
  });

  // Keep wheel/scroll inside the menu — do not bubble to page/modal
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

  // Close only when something *outside* the menu scrolls (page / modal body).
  // Scrolling the options list must keep the menu open.
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
