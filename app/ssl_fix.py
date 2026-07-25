"""Optional SSL tweaks for local Python 3.13+ on Windows.

Python 3.13+ enables VERIFY_X509_STRICT by default. Some CA certs in the
Windows trust store fail with:
  Basic Constraints of CA cert not marked critical

Additionally, requests/urllib3/boto3 often use only the certifi Mozilla bundle,
so corporate/AV MITM roots that exist in Windows are missing →
  unable to get local issuer certificate

Set SSL_RELAX_X509_STRICT=true in .env for local. Keep false on Railway.
"""

from __future__ import annotations

import logging
import ssl

logger = logging.getLogger(__name__)


def _relax_context(ctx: ssl.SSLContext) -> ssl.SSLContext:
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    if hasattr(ssl, "VERIFY_X509_PARTIAL_CHAIN"):
        ctx.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN
    return ctx


def _system_ssl_context() -> ssl.SSLContext:
    """Windows/macOS trust store via stdlib (not certifi-only)."""
    return _relax_context(ssl.create_default_context())


def apply_ssl_relax_if_configured() -> None:
    from config.settings import settings

    if not settings.SSL_RELAX_X509_STRICT:
        return
    if not hasattr(ssl, "VERIFY_X509_STRICT"):
        return

    # Capture ORIGINAL before patching (avoid recursion)
    _stdlib_create_default_context = ssl.create_default_context

    def relaxed_create_default_context(
        purpose=ssl.Purpose.SERVER_AUTH,
        *,
        cafile=None,
        capath=None,
        cadata=None,
    ):
        ctx = _stdlib_create_default_context(
            purpose, cafile=cafile, capath=capath, cadata=cadata
        )
        return _relax_context(ctx)

    ssl.create_default_context = relaxed_create_default_context  # type: ignore[assignment]
    ssl._create_default_https_context = relaxed_create_default_context  # type: ignore[attr-defined]

    # urllib3 / requests / boto3: prefer OS trust store + relaxed flags
    try:
        from urllib3.util import ssl_ as urllib3_ssl

        def relaxed_urllib3_context(*args, **kwargs):
            # Ignore certifi-only defaults — use OS store (needed for MITM/AV CAs)
            return _system_ssl_context()

        urllib3_ssl.create_urllib3_context = relaxed_urllib3_context  # type: ignore[assignment]
    except Exception:
        logger.debug("urllib3 SSL patch skipped", exc_info=True)

    try:
        from requests.adapters import HTTPAdapter

        _orig_init_poolmanager = HTTPAdapter.init_poolmanager

        def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
            pool_kwargs.setdefault("ssl_context", _system_ssl_context())
            return _orig_init_poolmanager(
                self, connections, maxsize, block=block, **pool_kwargs
            )

        HTTPAdapter.init_poolmanager = init_poolmanager  # type: ignore[method-assign]
    except Exception:
        logger.debug("requests SSL patch skipped", exc_info=True)

    logger.warning(
        "SSL_RELAX_X509_STRICT=true — trust store do SO + VERIFY_X509_STRICT off. "
        "So para desenvolvimento local; false em producao."
    )
