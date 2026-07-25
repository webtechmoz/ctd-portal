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
  wrap.appendChild(trigger);
  wrap.appendChild(menu);
  wrap._styledMenu = menu;

  const valueEl = trigger.querySelector(".styled-select-value");

  function paint() {
    const opt = select.selectedOptions[0];
    valueEl.textContent = opt ? opt.textContent : "—";
    menu.innerHTML = [...select.options]
      .map(
        (o) => `
      <button type="button" class="styled-select-option ${o.selected ? "active" : ""}" data-value="${escapeHtml(o.value)}" ${o.disabled ? "disabled" : ""}>
        ${escapeHtml(o.textContent)}
      </button>`
      )
      .join("");
  }

  function positionMenu() {
    const rect = trigger.getBoundingClientRect();
    const menuH = Math.min(menu.scrollHeight || 220, 220);
    const spaceBelow = window.innerHeight - rect.bottom - 8;
    const openUp = spaceBelow < menuH && rect.top > spaceBelow;
    menu.style.position = "fixed";
    menu.style.left = `${Math.max(8, rect.left)}px`;
    menu.style.minWidth = `${Math.max(rect.width, 120)}px`;
    menu.style.zIndex = "500";
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
    if (menu.parentNode !== wrap) wrap.appendChild(menu);
    menu.style.position = "";
    menu.style.top = "";
    menu.style.bottom = "";
    menu.style.left = "";
    menu.style.minWidth = "";
    menu.style.zIndex = "";
  }

  function open() {
    closeAllMenus(wrap);
    document.body.appendChild(menu);
    menu.hidden = false;
    wrap.classList.add("open");
    positionMenu();
  }

  trigger.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (menu.hidden) open();
    else close();
  });

  menu.addEventListener("click", (e) => {
    const btn = e.target.closest(".styled-select-option");
    if (!btn || btn.disabled) return;
    select.value = btn.dataset.value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    paint();
    close();
  });

  document.addEventListener("click", (e) => {
    if (!wrap.classList.contains("open")) return;
    if (wrap.contains(e.target) || menu.contains(e.target)) return;
    close();
  });

  window.addEventListener(
    "scroll",
    () => {
      if (wrap.classList.contains("open")) close();
    },
    true
  );
  window.addEventListener("resize", () => {
    if (wrap.classList.contains("open")) close();
  });

  paint();
  return { refresh: paint, close };
}
