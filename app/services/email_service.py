"""Email via Resend."""

from __future__ import annotations

import logging

from config.settings import settings

logger = logging.getLogger("ctd.email")


def _client():
    if not settings.RESEND_API_KEY:
        return None
    try:
        import resend

        resend.api_key = settings.RESEND_API_KEY
        return resend
    except Exception as exc:
        logger.warning("Resend indisponivel: %s", exc)
        return None


def send_email(*, to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Envia email. Devolve False se Resend nao estiver configurado (sem falhar o fluxo)."""
    client = _client()
    if not client:
        logger.info("Email nao enviado (RESEND_API_KEY ausente): %s — %s", to, subject)
        return False
    payload = {
        "from": settings.RESEND_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text
    try:
        client.Emails.send(payload)
        logger.info("Email enviado para %s: %s", to, subject)
        return True
    except Exception as exc:
        logger.exception("Falha ao enviar email para %s: %s", to, exc)
        return False


def send_credentials_email(
    *,
    name: str,
    email: str,
    password: str,
    login_url: str,
    reset: bool = False,
) -> bool:
    if reset:
        subject = f"{settings.APP_NAME} — credenciais redefinidas"
        intro = "A sua palavra-passe foi redefinida por um administrador."
    else:
        subject = f"{settings.APP_NAME} — as suas credenciais"
        intro = f"Foi criada uma conta no <strong>{settings.APP_NAME}</strong>."
    html = f"""
    <p>Ola <strong>{name}</strong>,</p>
    <p>{intro}</p>
    <p><strong>Email:</strong> {email}<br/>
    <strong>Palavra-passe temporaria:</strong> {password}</p>
    <p>No proximo acesso sera pedido que altere a palavra-passe.</p>
    <p><a href="{login_url}">Entrar no portal</a></p>
    """
    text = (
        f"Ola {name},\n\n"
        f"{'Palavra-passe redefinida' if reset else 'Conta criada'} no {settings.APP_NAME}.\n"
        f"Email: {email}\n"
        f"Palavra-passe temporaria: {password}\n"
        f"Login: {login_url}\n"
    )
    return send_email(to=email, subject=subject, html=html, text=text)


def send_simple_notice(*, to: str, subject: str, body: str, link: str | None = None) -> bool:
    link_html = f'<p><a href="{link}">Abrir no portal</a></p>' if link else ""
    html = f"<p>{body}</p>{link_html}"
    return send_email(to=to, subject=subject, html=html, text=body)
