/** Simple modal helper — focus, Escape, Enter confirma. */

import { closeStyledSelects } from "./styled-select.js";

function primaryAction(el) {
  return el.querySelector(".modal-foot .btn-primary, .modal-foot [data-modal-confirm]");
}

function bindKeys(el) {
  const onKey = (e) => {
    if (el.hidden) return;
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      closeModal(el);
      return;
    }
    if (e.key !== "Enter") return;
    const t = e.target;
    if (!(t instanceof HTMLElement)) return;
    // Textareas keep newline; buttons have their own activation
    if (t.tagName === "TEXTAREA") return;
    if (t.closest(".styled-select") || t.classList.contains("styled-select-trigger")) return;
    if (t.closest(".styled-select-menu")) return;
    if (t.matches("button, a, [type='submit']")) return;
    if (t.matches("input, select")) {
      e.preventDefault();
      primaryAction(el)?.click();
    }
  };
  el._modalKeyHandler = onKey;
  document.addEventListener("keydown", onKey, true);
}

function unbindKeys(el) {
  if (el._modalKeyHandler) {
    document.removeEventListener("keydown", el._modalKeyHandler, true);
    delete el._modalKeyHandler;
  }
}

export function openModal(el) {
  if (!el) return;
  closeStyledSelects();
  el.hidden = false;
  el.classList.add("open");
  document.body.classList.add("modal-open");
  bindKeys(el);
  requestAnimationFrame(() => {
    const focusable = el.querySelector(
      "input:not([type='hidden']), textarea, .styled-select-trigger, select, button.btn-primary"
    );
    focusable?.focus?.();
  });
}

export function closeModal(el) {
  if (!el) return;
  closeStyledSelects();
  unbindKeys(el);
  el.classList.remove("open");
  el.hidden = true;
  const stillOpen = [...document.querySelectorAll(".modal-backdrop")].some(
    (m) => m !== el && !m.hidden
  );
  if (!stillOpen) document.body.classList.remove("modal-open");
}

export function bindModalDismiss(el) {
  if (!el) return;
  el.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      closeModal(el);
    });
  });
  el.addEventListener("click", (e) => {
    if (e.target === el) closeModal(el);
  });
}
