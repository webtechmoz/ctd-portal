/** Login page. */
import { login, redirectIfAuthenticated } from "../auth.js";

redirectIfAuthenticated("/");

const form = document.getElementById("login-form");
const submitBtn = document.getElementById("btn_login");
const errorBox = document.getElementById("error_box");
const errorMsg = document.getElementById("error_msg");
const togglePw = document.getElementById("toggle_pw");
const passwordInput = document.getElementById("password");

function showError(message) {
  if (!errorBox || !errorMsg) return;
  errorMsg.textContent = message;
  errorBox.classList.add("show");
}

function clearError() {
  errorBox?.classList.remove("show");
}

togglePw?.addEventListener("click", () => {
  if (!passwordInput) return;
  const show = passwordInput.type === "password";
  passwordInput.type = show ? "text" : "password";
  togglePw.innerHTML = show ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';
});

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();
  const fd = new FormData(form);
  const email = String(fd.get("email") || "").trim();
  const password = String(fd.get("password") || "");

  if (!email || !password) {
    showError("Preencha todos os campos.");
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> A verificar...';
  }

  try {
    await login(email, password);
    window.location.href = "/";
  } catch (err) {
    showError(err.message || "Email ou password invalidos.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="bi bi-box-arrow-in-right"></i> Entrar';
    }
  }
});
