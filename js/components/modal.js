/** Simple modal helper. */

export function openModal(el) {
  if (!el) return;
  el.hidden = false;
  el.classList.add("open");
  document.body.classList.add("modal-open");
}

export function closeModal(el) {
  if (!el) return;
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
    btn.addEventListener("click", () => closeModal(el));
  });
  el.addEventListener("click", (e) => {
    if (e.target === el) closeModal(el);
  });
}
