"""Persistência e CRUD de credenciais de acesso ao Jira."""

from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CREDENTIALS_FILE = os.path.join(DATA_DIR, "credentials.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 8:
        return "*" * len(token)
    return f"{token[:4]}...{token[-4:]}"


def _ensure_storage() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as handle:
            json.dump({"credentials": []}, handle, indent=2, ensure_ascii=False)


def _load() -> dict[str, Any]:
    _ensure_storage()
    with open(CREDENTIALS_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def _save(data: dict[str, Any]) -> None:
    _ensure_storage()
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def _public_credential(credential: dict[str, Any], include_token: bool = False) -> dict[str, Any]:
    item = deepcopy(credential)
    token = item.get("api_token", "")
    if include_token:
        item["api_token_masked"] = _mask_token(token)
    else:
        item.pop("api_token", None)
        item["api_token_masked"] = _mask_token(token)
        item["has_token"] = bool(token)
    return item


def list_credentials() -> list[dict[str, Any]]:
    data = _load()
    return [_public_credential(item) for item in data.get("credentials", [])]


def get_credential(credential_id: str, include_token: bool = False) -> dict[str, Any] | None:
    data = _load()
    for item in data.get("credentials", []):
        if item.get("id") == credential_id:
            return _public_credential(item, include_token=include_token)
    return None


def get_credential_with_secret(credential_id: str) -> dict[str, Any] | None:
    data = _load()
    for item in data.get("credentials", []):
        if item.get("id") == credential_id:
            return deepcopy(item)
    return None


def get_default_credential(include_token: bool = False) -> dict[str, Any] | None:
    data = _load()
    credentials = data.get("credentials", [])
    if not credentials:
        return None

    default_item = next((item for item in credentials if item.get("is_default")), credentials[0])
    return _public_credential(default_item, include_token=include_token)


def get_default_credential_with_secret() -> dict[str, Any] | None:
    data = _load()
    credentials = data.get("credentials", [])
    if not credentials:
        return None
    return deepcopy(next((item for item in credentials if item.get("is_default")), credentials[0]))


def create_credential(payload: dict[str, Any]) -> dict[str, Any]:
    name = (payload.get("name") or "").strip()
    base_url = (payload.get("base_url") or "").strip().rstrip("/")
    email = (payload.get("email") or "").strip()
    api_token = (payload.get("api_token") or "").strip()

    if not name or not base_url or not email or not api_token:
        raise ValueError("Informe nome, URL, e-mail e token da API.")

    data = _load()
    credentials = data.setdefault("credentials", [])
    is_first = len(credentials) == 0

    credential = {
        "id": str(uuid.uuid4()),
        "name": name,
        "base_url": base_url,
        "email": email,
        "api_token": api_token,
        "is_default": bool(payload.get("is_default")) or is_first,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    if credential["is_default"]:
        for item in credentials:
            item["is_default"] = False

    credentials.append(credential)
    _save(data)
    return _public_credential(credential)


def update_credential(credential_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = _load()
    credentials = data.get("credentials", [])
    target = next((item for item in credentials if item.get("id") == credential_id), None)
    if not target:
        raise ValueError("Credencial não encontrada.")

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("Informe um nome para a conexão.")
        target["name"] = name

    if "base_url" in payload:
        base_url = (payload.get("base_url") or "").strip().rstrip("/")
        if not base_url:
            raise ValueError("Informe a URL do Jira.")
        target["base_url"] = base_url

    if "email" in payload:
        email = (payload.get("email") or "").strip()
        if not email:
            raise ValueError("Informe o e-mail Atlassian.")
        target["email"] = email

    if payload.get("api_token"):
        target["api_token"] = payload["api_token"].strip()

    if payload.get("is_default") is True:
        for item in credentials:
            item["is_default"] = item.get("id") == credential_id

    target["updated_at"] = _now_iso()
    _save(data)
    return _public_credential(target)


def delete_credential(credential_id: str) -> None:
    data = _load()
    credentials = data.get("credentials", [])
    remaining = [item for item in credentials if item.get("id") != credential_id]
    if len(remaining) == len(credentials):
        raise ValueError("Credencial não encontrada.")

    if remaining and not any(item.get("is_default") for item in remaining):
        remaining[0]["is_default"] = True

    data["credentials"] = remaining
    _save(data)


def set_default_credential(credential_id: str) -> dict[str, Any]:
    return update_credential(credential_id, {"is_default": True})


def import_from_env() -> dict[str, Any] | None:
    """Importa credencial do .env quando o armazenamento estiver vazio."""
    if list_credentials():
        return None

    base_url = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
    email = os.getenv("JIRA_EMAIL", "").strip()
    api_token = os.getenv("JIRA_API_TOKEN", "").strip()
    if not base_url or not email or not api_token:
        return None

    return create_credential(
        {
            "name": "Padrão (.env)",
            "base_url": base_url,
            "email": email,
            "api_token": api_token,
            "is_default": True,
        }
    )
