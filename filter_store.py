"""Persistência e CRUD de presets de filtros e etapas do relatório."""

from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from report_builder import DEFAULT_STATUSES

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FILTER_PRESETS_FILE = os.path.join(DATA_DIR, "filter_presets.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_storage() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(FILTER_PRESETS_FILE):
        with open(FILTER_PRESETS_FILE, "w", encoding="utf-8") as handle:
            json.dump({"presets": []}, handle, indent=2, ensure_ascii=False)


def _load() -> dict[str, Any]:
    _ensure_storage()
    with open(FILTER_PRESETS_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def _save(data: dict[str, Any]) -> None:
    _ensure_storage()
    with open(FILTER_PRESETS_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def _normalize_statuses(value: Any) -> list[str]:
    if not isinstance(value, list):
        return list(DEFAULT_STATUSES)
    statuses = [str(item).strip() for item in value if str(item).strip()]
    return statuses or list(DEFAULT_STATUSES)


def _public_preset(preset: dict[str, Any]) -> dict[str, Any]:
    item = deepcopy(preset)
    item["statuses"] = _normalize_statuses(item.get("statuses"))
    return item


def list_presets() -> list[dict[str, Any]]:
    data = _load()
    return [_public_preset(item) for item in data.get("presets", [])]


def get_preset(preset_id: str) -> dict[str, Any] | None:
    data = _load()
    for item in data.get("presets", []):
        if item.get("id") == preset_id:
            return _public_preset(item)
    return None


def get_default_preset() -> dict[str, Any] | None:
    data = _load()
    presets = data.get("presets", [])
    if not presets:
        return None
    default_item = next((item for item in presets if item.get("is_default")), presets[0])
    return _public_preset(default_item)


def create_preset(payload: dict[str, Any]) -> dict[str, Any]:
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("Informe um nome para o filtro.")

    data = _load()
    presets = data.setdefault("presets", [])
    is_first = len(presets) == 0

    preset = {
        "id": str(uuid.uuid4()),
        "name": name,
        "space_name": (payload.get("space_name") or "4AT - Geral").strip(),
        "project_key": (payload.get("project_key") or "GERAL4AT").strip(),
        "parent_key": (payload.get("parent_key") or "GERAL4AT-17").strip(),
        "dev_field": (payload.get("dev_field") or "").strip() or None,
        "impeditivo_field": (payload.get("impeditivo_field") or "").strip() or None,
        "statuses": _normalize_statuses(payload.get("statuses")),
        "report_mode": (payload.get("report_mode") or "full").strip(),
        "is_default": bool(payload.get("is_default")) or is_first,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    if preset["is_default"]:
        for item in presets:
            item["is_default"] = False

    presets.append(preset)
    _save(data)
    return _public_preset(preset)


def update_preset(preset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = _load()
    presets = data.get("presets", [])
    target = next((item for item in presets if item.get("id") == preset_id), None)
    if not target:
        raise ValueError("Filtro não encontrado.")

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("Informe um nome para o filtro.")
        target["name"] = name

    for field in ("space_name", "project_key", "parent_key", "report_mode"):
        if field in payload:
            target[field] = (payload.get(field) or "").strip()

    if "dev_field" in payload:
        target["dev_field"] = (payload.get("dev_field") or "").strip() or None

    if "impeditivo_field" in payload:
        target["impeditivo_field"] = (payload.get("impeditivo_field") or "").strip() or None

    if "statuses" in payload:
        target["statuses"] = _normalize_statuses(payload.get("statuses"))

    if payload.get("is_default") is True:
        for item in presets:
            item["is_default"] = item.get("id") == preset_id

    target["updated_at"] = _now_iso()
    _save(data)
    return _public_preset(target)


def delete_preset(preset_id: str) -> None:
    data = _load()
    presets = data.get("presets", [])
    remaining = [item for item in presets if item.get("id") != preset_id]
    if len(remaining) == len(presets):
        raise ValueError("Filtro não encontrado.")

    if remaining and not any(item.get("is_default") for item in remaining):
        remaining[0]["is_default"] = True

    data["presets"] = remaining
    _save(data)


def set_default_preset(preset_id: str) -> dict[str, Any]:
    return update_preset(preset_id, {"is_default": True})


def import_defaults() -> dict[str, Any] | None:
    """Cria preset UISA padrão quando o armazenamento estiver vazio."""
    if list_presets():
        return None

    return create_preset(
        {
            "name": "UISA",
            "space_name": "4AT - Geral",
            "project_key": "GERAL4AT",
            "parent_key": "GERAL4AT-17",
            "statuses": list(DEFAULT_STATUSES),
            "report_mode": "full",
            "is_default": True,
        }
    )
