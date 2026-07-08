"""Persistência e CRUD de conexões SMTP para envio de relatórios."""

from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EMAIL_CONNECTIONS_FILE = os.path.join(DATA_DIR, "email_connections.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}...{value[-2:]}"


def _parse_recipients(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
    return []


def _ensure_storage() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(EMAIL_CONNECTIONS_FILE):
        with open(EMAIL_CONNECTIONS_FILE, "w", encoding="utf-8") as handle:
            json.dump({"connections": []}, handle, indent=2, ensure_ascii=False)


def _load() -> dict[str, Any]:
    _ensure_storage()
    with open(EMAIL_CONNECTIONS_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def _save(data: dict[str, Any]) -> None:
    _ensure_storage()
    with open(EMAIL_CONNECTIONS_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def _public_connection(connection: dict[str, Any], include_password: bool = False) -> dict[str, Any]:
    item = deepcopy(connection)
    password = item.get("password", "")
    if include_password:
        item["password_masked"] = _mask_secret(password)
    else:
        item.pop("password", None)
        item["password_masked"] = _mask_secret(password)
        item["has_password"] = bool(password)
    return item


def list_connections() -> list[dict[str, Any]]:
    data = _load()
    return [_public_connection(item) for item in data.get("connections", [])]


def get_connection(connection_id: str, include_password: bool = False) -> dict[str, Any] | None:
    data = _load()
    for item in data.get("connections", []):
        if item.get("id") == connection_id:
            return _public_connection(item, include_password=include_password)
    return None


def get_connection_with_secret(connection_id: str) -> dict[str, Any] | None:
    data = _load()
    for item in data.get("connections", []):
        if item.get("id") == connection_id:
            return deepcopy(item)
    return None


def get_default_connection(include_password: bool = False) -> dict[str, Any] | None:
    data = _load()
    connections = data.get("connections", [])
    if not connections:
        return None
    default_item = next((item for item in connections if item.get("is_default")), connections[0])
    return _public_connection(default_item, include_password=include_password)


def get_default_connection_with_secret() -> dict[str, Any] | None:
    data = _load()
    connections = data.get("connections", [])
    if not connections:
        return None
    return deepcopy(next((item for item in connections if item.get("is_default")), connections[0]))


def _validate_connection_payload(payload: dict[str, Any], *, require_password: bool) -> dict[str, Any]:
    name = (payload.get("name") or "").strip()
    from_email = (payload.get("from_email") or "").strip()
    smtp_host = (payload.get("smtp_host") or "").strip()
    username = (payload.get("username") or from_email).strip()
    password = (payload.get("password") or "").strip()
    smtp_port = int(payload.get("smtp_port") or 587)
    use_tls = bool(payload.get("use_tls", True))
    default_recipients = _parse_recipients(payload.get("default_recipients", []))
    webhook_url = (payload.get("webhook_url") or "").strip()

    if not name:
        raise ValueError("Informe um nome para a conexão de e-mail.")
    if not from_email:
        raise ValueError("Informe o e-mail remetente.")
    if not smtp_host:
        raise ValueError("Informe o host SMTP.")
    if require_password and not password:
        raise ValueError("Informe a senha SMTP.")

    return {
        "name": name,
        "from_email": from_email,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "use_tls": use_tls,
        "username": username,
        "password": password,
        "default_recipients": default_recipients,
        "webhook_url": webhook_url,
        "is_default": bool(payload.get("is_default")),
    }


def create_connection(payload: dict[str, Any]) -> dict[str, Any]:
    validated = _validate_connection_payload(payload, require_password=True)
    data = _load()
    connections = data.setdefault("connections", [])
    is_first = len(connections) == 0

    connection = {
        "id": str(uuid.uuid4()),
        **validated,
        "is_default": validated["is_default"] or is_first,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    if connection["is_default"]:
        for item in connections:
            item["is_default"] = False

    connections.append(connection)
    _save(data)
    return _public_connection(connection)


def update_connection(connection_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = _load()
    connections = data.get("connections", [])
    target = next((item for item in connections if item.get("id") == connection_id), None)
    if not target:
        raise ValueError("Conexão de e-mail não encontrada.")

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("Informe um nome para a conexão de e-mail.")
        target["name"] = name

    if "from_email" in payload:
        from_email = (payload.get("from_email") or "").strip()
        if not from_email:
            raise ValueError("Informe o e-mail remetente.")
        target["from_email"] = from_email

    if "smtp_host" in payload:
        smtp_host = (payload.get("smtp_host") or "").strip()
        if not smtp_host:
            raise ValueError("Informe o host SMTP.")
        target["smtp_host"] = smtp_host

    if "smtp_port" in payload:
        target["smtp_port"] = int(payload.get("smtp_port") or 587)

    if "use_tls" in payload:
        target["use_tls"] = bool(payload.get("use_tls"))

    if "username" in payload:
        target["username"] = (payload.get("username") or "").strip()

    if payload.get("password"):
        target["password"] = payload["password"].strip()

    if "default_recipients" in payload:
        target["default_recipients"] = _parse_recipients(payload.get("default_recipients"))

    if "webhook_url" in payload:
        target["webhook_url"] = (payload.get("webhook_url") or "").strip()

    if payload.get("is_default") is True:
        for item in connections:
            item["is_default"] = item.get("id") == connection_id

    target["updated_at"] = _now_iso()
    _save(data)
    return _public_connection(target)


def delete_connection(connection_id: str) -> None:
    data = _load()
    connections = data.get("connections", [])
    remaining = [item for item in connections if item.get("id") != connection_id]
    if len(remaining) == len(connections):
        raise ValueError("Conexão de e-mail não encontrada.")

    if remaining and not any(item.get("is_default") for item in remaining):
        remaining[0]["is_default"] = True

    data["connections"] = remaining
    _save(data)


def set_default_connection(connection_id: str) -> dict[str, Any]:
    return update_connection(connection_id, {"is_default": True})


def import_from_env() -> dict[str, Any] | None:
    if list_connections():
        return None

    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.office365.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", from_email).strip()

    if not from_email or not password:
        return None

    return create_connection(
        {
            "name": "Office 365 (.env)",
            "from_email": from_email,
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "use_tls": True,
            "username": username,
            "password": password,
            "default_recipients": _parse_recipients(os.getenv("SMTP_DEFAULT_RECIPIENTS", "")),
            "is_default": True,
        }
    )
