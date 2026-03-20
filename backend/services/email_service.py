"""Email service using Resend.

Provides synchronous interfaces for API and worker processes. Delivery must
either succeed or fail clearly; missing provider configuration is treated as an
operational error instead of a silent skip.
"""

import logging
from typing import Any

import resend

from backend.config import get_settings

logger = logging.getLogger(__name__)

_initialized = False


def _ensure_initialized() -> bool:
    """Lazy-initialize Resend API key. Returns True if ready."""
    global _initialized
    if _initialized:
        return True

    settings = get_settings()
    if not settings.resend_api_key:
        logger.error("RESEND_API_KEY is not set; email delivery is unavailable.")
        return False

    resend.api_key = settings.resend_api_key
    _initialized = True
    return True


def send_email(
    to: str | list[str],
    subject: str,
    html: str,
    *,
    reply_to: str | None = None,
    tags: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Send an email via Resend (synchronous)."""
    settings = get_settings()

    if not _ensure_initialized():
        raise RuntimeError(
            "Email delivery is not configured: RESEND_API_KEY is missing"
        )

    recipients = [to] if isinstance(to, str) else to

    params: dict[str, Any] = {
        "from_": settings.resend_from_email,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        params["reply_to"] = reply_to
    if tags:
        params["tags"] = tags

    try:
        response = resend.Emails.send(params)  # type: ignore[arg-type]
        resp_id = (
            response.get("id")
            if isinstance(response, dict)
            else getattr(response, "id", None)
        )
        logger.info(
            "Email sent via Resend: id=%s to=%s subject=%s",
            resp_id,
            recipients,
            subject,
        )
        if isinstance(response, dict):
            response.setdefault("status", "sent")
            return response  # type: ignore[return-value]
        return {"id": getattr(response, "id", None), "status": "sent"}
    except Exception:
        logger.exception(
            "Failed to send email via Resend: to=%s subject=%s", recipients, subject
        )
        raise


def send_deletion_request_email(
    to: str,
    request_id: str,
) -> dict[str, Any]:
    """Send confirmation email for GDPR data deletion request."""
    subject = "Data deletion request received - Cogent"
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Data Deletion Request Received</h2>
        <p>Hi there,</p>
        <p>We've received your request to delete your account data.</p>
        <ul>
            <li><strong>Request ID:</strong> {request_id}</li>
            <li><strong>Grace period:</strong> 30 days</li>
        </ul>
        <p>Your account data will be permanently removed after the 30-day grace
        period. If you change your mind, you can cancel this request by
        contacting our support team before the grace period ends.</p>
        <p>- The Cogent Team</p>
    </div>
    """
    return send_email(
        to=to,
        subject=subject,
        html=html,
        tags=[{"name": "category", "value": "gdpr_deletion"}],
    )


def send_data_export_request_email(
    to: str,
    request_id: str,
) -> dict[str, Any]:
    """Send confirmation email for data export request."""
    subject = "Data export request received - Cogent"
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Data Export Request Received</h2>
        <p>Hi there,</p>
        <p>We've received your request to export your account data.</p>
        <ul>
            <li><strong>Request ID:</strong> {request_id}</li>
        </ul>
        <p>We'll prepare a full archive of your contracts, briefs, and history
        and email it to this address within 24 hours.</p>
        <p>- The Cogent Team</p>
    </div>
    """
    return send_email(
        to=to,
        subject=subject,
        html=html,
        tags=[{"name": "category", "value": "data_export"}],
    )
