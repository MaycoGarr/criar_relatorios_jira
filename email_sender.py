"""Envio de e-mails via SMTP (Office 365 e compatíveis)."""

from __future__ import annotations

import json
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
EMAIL_LOGS_FILE = DATA_DIR / "email_logs.json"


def _append_log(entry: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logs: list[dict[str, Any]] = []
    if EMAIL_LOGS_FILE.exists():
        with open(EMAIL_LOGS_FILE, encoding="utf-8") as handle:
            logs = json.load(handle).get("logs", [])
    logs.insert(0, entry)
    logs = logs[:100]
    with open(EMAIL_LOGS_FILE, "w", encoding="utf-8") as handle:
        json.dump({"logs": logs}, handle, indent=2, ensure_ascii=False)


def send_email(
    connection: dict[str, Any],
    *,
    subject: str,
    text_body: str,
    html_body: str,
    recipients: list[str] | None = None,
) -> dict[str, Any]:
    to_addresses = recipients or connection.get("default_recipients") or []
    if not to_addresses:
        raise ValueError("Informe ao menos um destinatário.")

    from_email = connection["from_email"]
    username = connection.get("username") or from_email
    password = connection.get("password", "")
    smtp_host = connection["smtp_host"]
    smtp_port = int(connection.get("smtp_port") or 587)
    use_tls = bool(connection.get("use_tls", True))

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = ", ".join(to_addresses)
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=60) as server:
            if use_tls:
                server.starttls(context=ssl.create_default_context())
            server.login(username, password)
            server.sendmail(from_email, to_addresses, message.as_string())

        result = {
            "ok": True,
            "recipients": to_addresses,
            "subject": subject,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        _append_log({**result, "status": "success", "connection_id": connection.get("id")})
        return result
    except Exception as error:
        _append_log(
            {
                "ok": False,
                "status": "error",
                "error": str(error),
                "recipients": to_addresses,
                "subject": subject,
                "connection_id": connection.get("id"),
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        raise
