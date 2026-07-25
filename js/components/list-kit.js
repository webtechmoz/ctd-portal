/** Client-side search + pagination for tables and card grids. */

/**
 * Dynamic multi-token search over any relevant fields.
 * @param {unknown[]} items
 * @param {string} query
 * @param {(item: any) => Array<string|number|null|undefined>} getFields
 */
export function filterByQuery(items, query, getFields) {
  const q = String(query || "")
    .trim()
    .toLowerCase();
  if (!q) return items;
  const tokens = q.split(/\s+/).filter(Boolean);
  return items.filter((item) => {
    const hay = getFields(item)
      .map((v) => String(v ?? "").toLowerCase())
      .join(" ");
    return tokens.every((t) => hay.includes(t));
  });
}

/**
 * @param {unknown[]} items
 * @param {number} page 1-based
 * @param {number} pageSize
 */
export function paginate(items, page, pageSize) {
  const size = Math.max(1, pageSize || 10);
  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / size) || 1);
  const safePage = Math.min(Math.max(1, page || 1), pages);
  const start = (safePage - 1) * size;
  return {
    items: items.slice(start, start + size),
    page: safePage,
    pages,
    total,
    from: total ? start + 1 : 0,
    to: Math.min(start + size, total),
  };
}

/**
 * Mount search input + pager under a host element.
 * @param {HTMLElement} host
 * @param {{ placeholder?: string, pageSize?: number, onChange?: () => void }} opts
 */
export function mountSearchPager(host, opts = {}) {
  if (!host) {
    return {
      query: "",
      page: 1,
      pageSize: opts.pageSize || 10,
      setMeta() {},
      reset() {},
    };
  }

  const pageSize = opts.pageSize || 10;
  let query = "";
  let page = 1;
  let debounce = null;

  host.classList.add("list-controls");
  host.innerHTML = `
    <div class="search-field">
      <i class="bi bi-search" aria-hidden="true"></i>
      <input type="search" class="search-input" placeholder="${opts.placeholder || "Pesquisar..."}" autocomplete="off" />
    </div>
    <div class="pager" hidden>
      <span class="pager-meta"></span>
      <div class="pager-btns">
        <button type="button" class="pager-btn" data-pager="prev" aria-label="Anterior"><i class="bi bi-chevron-left"></i></button>
        <span class="pager-page"></span>
        <button type="button" class="pager-btn" data-pager="next" aria-label="Seguinte"><i class="bi bi-chevron-right"></i></button>
      </div>
    </div>
  `;

  const input = host.querySelector(".search-input");
  const pager = host.querySelector(".pager");
  const meta = host.querySelector(".pager-meta");
  const pageLabel = host.querySelector(".pager-page");
  const btnPrev = host.querySelector('[data-pager="prev"]');
  const btnNext = host.querySelector('[data-pager="next"]');

  function notify() {
    opts.onChange?.();
  }

  input.addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      query = input.value;
      page = 1;
      notify();
    }, 160);
  });

  btnPrev.addEventListener("click", () => {
    if (page <= 1) return;
    page -= 1;
    notify();
  });
  btnNext.addEventListener("click", () => {
    page += 1;
    notify();
  });

  return {
    get query() {
      return query;
    },
    get page() {
      return page;
    },
    get pageSize() {
      return pageSize;
    },
    setMeta({ total, page: p, pages, from, to }) {
      page = p;
      if (!total) {
        pager.hidden = true;
        return;
      }
      pager.hidden = false;
      meta.textContent = `${from}–${to} de ${total}`;
      pageLabel.textContent = `${p} / ${pages}`;
      btnPrev.disabled = p <= 1;
      btnNext.disabled = p >= pages;
    },
    reset() {
      query = "";
      page = 1;
      input.value = "";
      notify();
    },
  };
}
