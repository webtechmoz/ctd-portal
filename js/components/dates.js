/** Flatpickr helpers (Y-m-d). */

const PT = {
  weekdays: {
    shorthand: ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"],
    longhand: [
      "Domingo",
      "Segunda",
      "Terca",
      "Quarta",
      "Quinta",
      "Sexta",
      "Sabado",
    ],
  },
  months: {
    shorthand: [
      "Jan",
      "Fev",
      "Mar",
      "Abr",
      "Mai",
      "Jun",
      "Jul",
      "Ago",
      "Set",
      "Out",
      "Nov",
      "Dez",
    ],
    longhand: [
      "Janeiro",
      "Fevereiro",
      "Marco",
      "Abril",
      "Maio",
      "Junho",
      "Julho",
      "Agosto",
      "Setembro",
      "Outubro",
      "Novembro",
      "Dezembro",
    ],
  },
  firstDayOfWeek: 1,
  rangeSeparator: " ate ",
  time_24hr: true,
};

/**
 * @param {HTMLInputElement|string} input
 * @param {{ defaultDate?: string|null, minDate?: string|Date|null, onChange?: (iso:string)=>void }} [opts]
 */
export function bindDatePicker(input, opts = {}) {
  const el = typeof input === "string" ? document.querySelector(input) : input;
  if (!el) return null;
  if (typeof window.flatpickr !== "function") {
    el.type = "date";
    if (opts.minDate) el.min = typeof opts.minDate === "string" ? opts.minDate : addDaysISO(0);
    return null;
  }
  if (el._flatpickr) {
    el._flatpickr.destroy();
  }
  return window.flatpickr(el, {
    locale: PT,
    dateFormat: "Y-m-d",
    altInput: true,
    altFormat: "d/m/Y",
    allowInput: false,
    disableMobile: true,
    defaultDate: opts.defaultDate || el.value || null,
    minDate: opts.minDate ?? undefined,
    onChange(selected) {
      const iso = selected[0] ? window.flatpickr.formatDate(selected[0], "Y-m-d") : "";
      opts.onChange?.(iso);
    },
  });
}

export function addDaysISO(days) {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + Number(days || 0));
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
