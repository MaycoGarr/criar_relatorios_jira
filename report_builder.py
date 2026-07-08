"""Montagem do relatório textual a partir dos cards do Jira."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from email_template import build_email_html
from jira_client import JiraClient
from report_template import build_status_report_html, is_entregue_status

DEFAULT_STATUSES = [
    "MAPEAMENTO",
    "PRONTO PARA DESENVOLVER",
    "DESENVOLVIMENTO",
    "TESTES INTERNOS",
    "HOMOLOGAÇÃO",
    "ITENS CONCLUÍDOS",
]

UPDATE_SUMMARY_MAX_LEN_DEFAULT = 280
UPDATE_SUMMARY_MAX_LEN_EXEC = 480
UPDATE_SUMMARY_MAX_LEN_DISPLAY = 520

SUBTASK_ISSUE_TYPES = {"sub-task", "subtarefa", "sub task"}

IMPEDITIVO_FIELD_CANDIDATES = [
    "flag impeditivo",
    "impeditivo",
    "impedimento",
    "flag impedimento",
    "flagged",
    "flag",
]

DEV_FIELD_CANDIDATES = [
    "dev. responsável",
    "dev responsável",
    "desenvolvedor responsável",
    "responsável dev",
    "responsavel dev",
    "responsável",
    "responsavel",
]

STATUS_ALIASES: dict[str, list[str]] = {
    "MAPEAMENTO": ["mapeamento"],
    "PRONTO PARA DESENVOLVER": ["pronto para desenvolver"],
    "DESENVOLVIMENTO": ["desenvolvimento"],
    "TESTES INTERNOS": ["testes internos"],
    "HOMOLOGAÇÃO": ["homologação", "homologacao"],
    "ITENS CONCLUÍDOS": ["itens concluídos", "itens concluidos", "concluído", "concluido"],
}

NOISE_CHANGELOG_FIELDS = {
    "assignee",
    "responsável",
    "responsavel",
    "flagged",
    "flag",
    "status",
    "priority",
    "prioridade",
    "rank",
    "sprint",
    "story points",
}

FLAG_PREFIX_RE = re.compile(r"^flag\s+added\s*", re.IGNORECASE)
_WA_DIVIDER = "━━━━━━━━━━━━━━━━"


def _status_sort_key(status_name: str) -> int:
    normalized = _normalize_text(status_name)
    for index, canonical in enumerate(DEFAULT_STATUSES):
        if normalized == _normalize_text(canonical):
            return index
        for alias in STATUS_ALIASES.get(canonical, []):
            if normalized == alias:
                return index
    return 999


def _parse_datetime(value: str | None, timezone: str = "America/Sao_Paulo") -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if _timezone_available(timezone):
            return parsed.astimezone(ZoneInfo(timezone))
        return parsed.astimezone()
    except ValueError:
        return None


def _parse_jira_datetime(value: str | None, timezone: str = "America/Sao_Paulo") -> datetime | None:
    return _parse_datetime(value, timezone)


def _days_since_update(update_iso: str | None, timezone: str = "America/Sao_Paulo") -> int | None:
    parsed = _parse_datetime(update_iso, timezone)
    if not parsed:
        return None
    now = _local_now(timezone)
    return max((now.date() - parsed.date()).days, 0)


def _build_issue_url(base_url: str, issue_key: str) -> str:
    return f"{base_url.rstrip('/')}/browse/{issue_key}"


def _build_report_title(parent_key: str, parent_label: str | None) -> str:
    if parent_label and parent_label != parent_key:
        return f"RELATÓRIO JIRA — {parent_key} ({parent_label})"
    if parent_label:
        return f"RELATÓRIO JIRA — {parent_label}"
    return f"RELATÓRIO JIRA — {parent_key}"


def build_email_subject(report: dict[str, Any], parent_label: str | None = None) -> str:
    label = parent_label or report.get("parent_label") or report.get("parent_key", "")
    impeditive_count = report.get("impeditive_count", 0)
    generated_at = report.get("generated_at", "")
    mode = report.get("mode", "full")

    if mode == "impeditive_only":
        return f"[{label}] {impeditive_count} impeditivo(s) — Relatório Jira {generated_at}"
    if impeditive_count > 0:
        return f"[{label}] {impeditive_count} impeditivo(s) — Relatório Jira {generated_at}"
    return f"[{label}] Relatório Jira {generated_at}"


def build_report_subject(report: dict[str, Any], parent_label: str | None = None) -> str:
    label = parent_label or report.get("parent_label") or report.get("parent_key", "")
    generated_at = report.get("generated_at", "")
    return f"[{label}] Status Report Visual — {generated_at}"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _timezone_available(timezone: str) -> bool:
    try:
        ZoneInfo(timezone)
        return True
    except Exception:
        return False


def _local_now(timezone: str = "America/Sao_Paulo") -> datetime:
    if _timezone_available(timezone):
        return datetime.now(ZoneInfo(timezone))
    return datetime.now().astimezone()


def _adf_to_text(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_adf_to_text(item) for item in node)
    if isinstance(node, dict):
        text = node.get("text", "")
        content = _adf_to_text(node.get("content", []))
        return f"{text}{content}"
    return str(node)


def _format_datetime(value: str | None, timezone: str = "America/Sao_Paulo") -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        try:
            local = parsed.astimezone(ZoneInfo(timezone))
        except Exception:
            local = parsed.astimezone(datetime.now().astimezone().tzinfo)
        return local.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return value


def _find_custom_field_id(
    fields_meta: list[dict[str, Any]], candidates: list[str]
) -> str | None:
    normalized_candidates = {_normalize_text(name) for name in candidates}
    for field in fields_meta:
        name = _normalize_text(field.get("name", ""))
        if name in normalized_candidates:
            return field.get("id")
    for field in fields_meta:
        name = _normalize_text(field.get("name", ""))
        if any(candidate in name for candidate in normalized_candidates):
            return field.get("id")
    return None


def _extract_user_name(value: Any) -> str:
    if not value:
        return "Não informado"
    if isinstance(value, dict):
        return value.get("displayName") or value.get("name") or "Não informado"
    return str(value)


def _extract_impeditivo(value: Any) -> str:
    if value is None:
        return "Não"
    if isinstance(value, list):
        return "Sim" if len(value) > 0 else "Não"
    if isinstance(value, dict):
        text = value.get("value") or value.get("name") or ""
        if not text:
            return "Sim"
        return "Sim" if _normalize_text(str(text)) not in {"não", "nao", "no", "false"} else "Não"
    text = str(value).strip()
    if not text:
        return "Não"
    return "Sim" if _normalize_text(text) in {"sim", "yes", "true"} else "Não"


def resolve_statuses(
    available_statuses: list[str], requested_statuses: list[str]
) -> list[str]:
    if not available_statuses:
        return requested_statuses

    normalized_available = {_normalize_text(status): status for status in available_statuses}
    resolved: list[str] = []

    for status in requested_statuses:
        normalized = _normalize_text(status)
        if normalized in normalized_available:
            resolved.append(normalized_available[normalized])
            continue

        aliases = STATUS_ALIASES.get(status.upper(), [normalized])
        matched_name: str | None = None
        for alias in aliases:
            if alias in normalized_available:
                matched_name = normalized_available[alias]
                break

        if not matched_name:
            for available_normalized, available_name in normalized_available.items():
                if normalized in available_normalized or available_normalized in normalized:
                    matched_name = available_name
                    break
                if status.upper() == "ITENS CONCLUÍDOS" and "conclu" in available_normalized:
                    matched_name = available_name
                    break

        if matched_name:
            resolved.append(matched_name)

    return list(dict.fromkeys(resolved))


def _build_jql(
    parent_key: str,
    statuses: list[str],
    project_key: str | None = None,
    space_name: str | None = None,
) -> str:
    clauses: list[str] = []

    if project_key:
        clauses.append(f'project = "{project_key}"')

    if parent_key:
        clauses.append(f"parent = {parent_key}")

    if statuses:
        quoted = ", ".join(f'"{status}"' for status in statuses)
        clauses.append(f"status IN ({quoted})")

    if space_name and not project_key:
        clauses.append(f'project = "{space_name}"')

    jql = " AND ".join(clauses) if clauses else "ORDER BY updated DESC"
    return jql


def _build_parent_jql(
    parent_key: str,
    project_key: str | None = None,
    *,
    extra_clauses: list[str] | None = None,
) -> str:
    clauses: list[str] = []
    if project_key:
        clauses.append(f'project = "{project_key}"')
    if parent_key:
        clauses.append(f"parent = {parent_key}")
    if extra_clauses:
        clauses.extend(extra_clauses)
    return " AND ".join(clauses) if clauses else "ORDER BY updated DESC"


def _is_parent_level_issue(issue: dict[str, Any]) -> bool:
    fields = issue.get("fields", {})
    issuetype = fields.get("issuetype") or {}
    if issuetype.get("subtask"):
        return False
    name = _normalize_text(issuetype.get("name", ""))
    return name not in SUBTASK_ISSUE_TYPES


def _delivered_at_from_issue(
    issue: dict[str, Any],
    timezone: str = "America/Sao_Paulo",
) -> datetime | None:
    fields = issue.get("fields", {})
    for field_name in ("resolutiondate", "statuscategorychangedate", "updated"):
        parsed = _parse_jira_datetime(fields.get(field_name), timezone)
        if parsed:
            return parsed
    return None


def _summarize_delivered_stats(
    delivered_cards: list[dict[str, Any]],
    *,
    timezone: str = "America/Sao_Paulo",
) -> dict[str, int | list[str]]:
    now = _local_now(timezone)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    mes_itens: list[str] = []
    for card in delivered_cards:
        delivered_at = _parse_jira_datetime(card.get("entregue_em"), timezone)
        if delivered_at is None or delivered_at < month_start:
            continue
        mes_itens.append(str(card.get("summary") or card.get("key", "")))

    return {
        "entregues_mes": len(mes_itens),
        "entregues_total": len(delivered_cards),
        "entregues_mes_itens": mes_itens,
    }


def _issue_to_card(
    issue: dict[str, Any],
    *,
    client: JiraClient,
    dev_field: str,
    impeditivo_field: str | None,
    timezone: str,
    base_url: str,
) -> dict[str, Any]:
    fields = issue.get("fields", {})
    issue_key = issue.get("key", "")
    dev_value = fields.get(dev_field) if dev_field else fields.get("assignee")
    impeditivo_value = fields.get(impeditivo_field) if impeditivo_field else None
    update_text, update_date, update_raw = _get_last_update(client, issue_key, timezone)
    days_stale = _days_since_update(update_raw, timezone)
    status_name = (fields.get("status") or {}).get("name", "Sem etapa")

    return {
        "key": issue_key,
        "summary": fields.get("summary", ""),
        "status": status_name,
        "dev_responsavel": _extract_user_name(dev_value),
        "impeditivo": _extract_impeditivo(impeditivo_value),
        "ultima_atualizacao": update_text,
        "ultima_atualizacao_resumo": _summarize_update(update_text),
        "ultima_atualizacao_resumo_executivo": _summarize_update(
            update_text, max_len=UPDATE_SUMMARY_MAX_LEN_EXEC
        ),
        "ultima_atualizacao_exibicao": _summarize_update(
            update_text, max_len=UPDATE_SUMMARY_MAX_LEN_DISPLAY
        ),
        "ultima_atualizacao_data": update_date,
        "dias_sem_atualizacao": days_stale,
        "jira_url": _build_issue_url(base_url, issue_key),
        "progresso_subtarefas": None,
        "progresso_subtarefas_concluidas": None,
        "progresso_subtarefas_total": None,
    }


def _issue_to_delivered_card(
    issue: dict[str, Any],
    *,
    client: JiraClient,
    dev_field: str,
    impeditivo_field: str | None,
    timezone: str,
    base_url: str,
) -> dict[str, Any]:
    card = _issue_to_card(
        issue,
        client=client,
        dev_field=dev_field,
        impeditivo_field=impeditivo_field,
        timezone=timezone,
        base_url=base_url,
    )
    delivered_at = _delivered_at_from_issue(issue, timezone)
    if delivered_at:
        card["entregue_em"] = delivered_at.isoformat()
        card["entregue_em_label"] = delivered_at.strftime("%d/%m/%Y")
    return card


def _fetch_delivered_cards(
    client: JiraClient,
    *,
    parent_key: str,
    project_key: str | None,
    dev_field: str,
    impeditivo_field: str | None,
    timezone: str,
    base_url: str,
) -> list[dict[str, Any]]:
    if not parent_key:
        return []

    requested_fields = [
        "summary",
        "status",
        "assignee",
        "parent",
        "issuetype",
        "resolutiondate",
        "statuscategorychangedate",
        "updated",
    ]
    if impeditivo_field:
        requested_fields.append(impeditivo_field)
    if dev_field and dev_field not in requested_fields:
        requested_fields.append(dev_field)

    parent_only_clause = 'issuetype not in (Sub-task, Subtarefa)'
    jql = _build_parent_jql(parent_key, project_key, extra_clauses=[parent_only_clause])
    issues = client.search_issues(jql, fields=requested_fields)

    def _build_delivered(issue_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        delivered: list[dict[str, Any]] = []
        for issue in issue_list:
            if not _is_parent_level_issue(issue):
                continue
            status_name = (issue.get("fields", {}).get("status") or {}).get("name", "")
            if not is_entregue_status(status_name):
                continue
            delivered.append(
                _issue_to_delivered_card(
                    issue,
                    client=client,
                    dev_field=dev_field,
                    impeditivo_field=impeditivo_field,
                    timezone=timezone,
                    base_url=base_url,
                )
            )
        return delivered

    delivered = _build_delivered(issues)
    if delivered:
        return delivered

    fallback_jql = _build_parent_jql(
        parent_key,
        project_key,
        extra_clauses=[parent_only_clause, "statusCategory = Done"],
    )
    try:
        fallback_issues = client.search_issues(fallback_jql, fields=requested_fields)
    except Exception:
        return []

    return _build_delivered(fallback_issues)


def get_board_people(
    client: JiraClient,
    *,
    parent_key: str,
    project_key: str | None,
    dev_field: str | None = None,
) -> list[str]:
    if not parent_key:
        return []

    discovered = discover_field_ids(client)
    resolved_dev_field = dev_field or discovered["dev_responsavel"]
    fields = [resolved_dev_field] if resolved_dev_field else ["assignee"]
    jql = _build_parent_jql(parent_key, project_key)
    issues = client.search_issues(jql, fields=fields)

    names: set[str] = set()
    for issue in issues:
        fields_data = issue.get("fields", {})
        dev_value = (
            fields_data.get(resolved_dev_field)
            if resolved_dev_field
            else fields_data.get("assignee")
        )
        name = _extract_user_name(dev_value)
        if name and name != "Não informado":
            names.add(name)

    return sorted(names, key=str.lower)


def _count_delivered_projects(
    client: JiraClient,
    *,
    parent_key: str,
    project_key: str | None,
    project_statuses: list[str],
    dev_field: str,
    impeditivo_field: str | None,
    timezone: str,
    base_url: str,
) -> int:
    return len(
        _fetch_delivered_cards(
            client,
            parent_key=parent_key,
            project_key=project_key,
            dev_field=dev_field,
            impeditivo_field=impeditivo_field,
            timezone=timezone,
            base_url=base_url,
        )
    )


def _clean_update_text(text: str) -> str:
    cleaned = FLAG_PREFIX_RE.sub("", text or "").strip()
    return cleaned or "Sem conteúdo na última atualização."


def _summarize_update(text: str, max_len: int = UPDATE_SUMMARY_MAX_LEN_DEFAULT) -> str:
    cleaned = " ".join(_clean_update_text(text).split())
    if cleaned == "Sem conteúdo na última atualização.":
        return cleaned
    if len(cleaned) <= max_len:
        return cleaned

    for sep in (". ", "! ", "? ", "; "):
        idx = cleaned.find(sep)
        if 0 < idx <= max_len:
            return cleaned[: idx + 1].strip()

    truncated = cleaned[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > int(max_len * 0.6):
        truncated = truncated[:last_space]
    return truncated.rstrip(".,;") + "…"


def _is_desenvolvimento_etapa(status_name: str) -> bool:
    normalized = _normalize_text(status_name)
    aliases = [_normalize_text("DESENVOLVIMENTO"), *STATUS_ALIASES.get("DESENVOLVIMENTO", [])]
    return normalized in aliases


def _is_subtask_done(status: dict[str, Any]) -> bool:
    category = ((status or {}).get("statusCategory") or {}).get("key", "")
    if category == "done":
        return True
    name = _normalize_text((status or {}).get("name", ""))
    return any(token in name for token in ("conclu", "done", "finaliz"))


def _compute_subtask_progress_detail(
    subtasks: list[dict[str, Any]],
) -> tuple[int | None, int | None, int | None]:
    if not subtasks:
        return None, None, None
    total = len(subtasks)
    done_count = sum(
        1
        for issue in subtasks
        if _is_subtask_done((issue.get("fields") or {}).get("status", {}))
    )
    percent = round((done_count / total) * 100)
    return percent, done_count, total


def _compute_subtask_progress(subtasks: list[dict[str, Any]]) -> int | None:
    percent, _, _ = _compute_subtask_progress_detail(subtasks)
    return percent


def _extract_progress_percent(progress_data: Any) -> int | None:
    if not isinstance(progress_data, dict):
        return None

    percent = progress_data.get("percent")
    if percent is not None:
        return max(0, min(100, int(percent)))

    total = progress_data.get("total") or 0
    progress = progress_data.get("progress") or 0
    if total > 0:
        return max(0, min(100, round((progress / total) * 100)))
    return None


def _average_subtask_progress_percent(subtasks: list[dict[str, Any]]) -> int | None:
    values: list[int] = []
    for issue in subtasks:
        fields = issue.get("fields") or {}
        percent = _extract_progress_percent(fields.get("progress"))
        if percent is not None:
            values.append(percent)
    if not values:
        return None
    return round(sum(values) / len(values))


def _has_meaningful_jira_progress(progress_data: Any) -> bool:
    if not isinstance(progress_data, dict):
        return False
    total = progress_data.get("total") or 0
    if total > 0:
        return True
    percent = progress_data.get("percent")
    return percent is not None and int(percent) > 0


def _resolve_card_progress(
    aggregate_data: Any,
    subtasks: list[dict[str, Any]],
) -> tuple[int | None, int | None, int | None]:
    if subtasks:
        status_percent, done_count, total = _compute_subtask_progress_detail(subtasks)
        if status_percent is not None:
            return status_percent, done_count, total

    if _has_meaningful_jira_progress(aggregate_data):
        jira_percent = _extract_progress_percent(aggregate_data)
        if jira_percent is not None:
            return jira_percent, None, None

    time_percent = _average_subtask_progress_percent(subtasks) if subtasks else None
    if time_percent is not None:
        return time_percent, None, len(subtasks) if subtasks else None

    return None, None, None


def _attach_card_progress(
    client: JiraClient,
    cards: list[dict[str, Any]],
    issue_aggregate: dict[str, Any],
    issue_subtask_keys: dict[str, list[str]],
) -> None:
    if not cards:
        return

    card_keys = [card["key"] for card in cards]
    grouped = client.get_subtasks_for_parents(card_keys, issue_subtask_keys)

    for card in cards:
        subtasks = grouped.get(card["key"], [])
        percent, done, total = _resolve_card_progress(
            issue_aggregate.get(card["key"]),
            subtasks,
        )
        card["progresso_subtarefas"] = percent
        card["progresso_subtarefas_concluidas"] = done
        card["progresso_subtarefas_total"] = total


def _is_noise_changelog_item(item: dict[str, Any]) -> bool:
    field_name = _normalize_text(str(item.get("field", "")))
    return any(noise in field_name for noise in NOISE_CHANGELOG_FIELDS)


def _get_last_update(
    client: JiraClient, issue_key: str, timezone: str = "America/Sao_Paulo"
) -> tuple[str, str, str | None]:
    comments = client.get_issue_comments(issue_key)
    if comments:
        for comment in sorted(comments, key=lambda item: item.get("created", ""), reverse=True):
            raw_body = _adf_to_text(comment.get("body")).strip()
            body = _clean_update_text(raw_body)
            if body == "Sem conteúdo na última atualização.":
                continue
            created_raw = comment.get("created", "")
            created = _format_datetime(created_raw, timezone)
            return body, created, created_raw

    histories = client.get_issue_changelog(issue_key)
    meaningful_histories = []
    for history in histories:
        items = history.get("items", [])
        meaningful_items = [item for item in items if not _is_noise_changelog_item(item)]
        if meaningful_items:
            meaningful_histories.append((history, meaningful_items))

    if meaningful_histories:
        latest_history, items = max(meaningful_histories, key=lambda pair: pair[0].get("created", ""))
        item = items[-1]
        message = (
            f"{item.get('field', 'Campo')} alterado de "
            f"\"{item.get('fromString', '-')}\" para \"{item.get('toString', '-')}\""
        )
        created_raw = latest_history.get("created", "")
        return message, _format_datetime(created_raw, timezone), created_raw

    if histories:
        latest = max(histories, key=lambda item: item.get("created", ""))
        created_raw = latest.get("created", "")
        return "Atualização registrada no histórico do card.", _format_datetime(created_raw, timezone), created_raw

    return "Nenhuma atualização encontrada.", "", None


def discover_field_ids(client: JiraClient) -> dict[str, str | None]:
    fields_meta = client.get_fields()
    impeditivo = _find_custom_field_id(fields_meta, IMPEDITIVO_FIELD_CANDIDATES)
    dev_responsavel = _find_custom_field_id(fields_meta, DEV_FIELD_CANDIDATES)

    if not impeditivo:
        impeditivo = "customfield_10000"

    if not dev_responsavel:
        dev_responsavel = "assignee"

    return {
        "impeditivo": impeditivo,
        "dev_responsavel": dev_responsavel,
    }


def build_report(
    client: JiraClient,
    *,
    parent_key: str = "GERAL4AT-17",
    parent_label: str | None = None,
    project_key: str | None = "GERAL4AT",
    space_name: str | None = "4AT - Geral",
    statuses: list[str] | None = None,
    impeditivo_field: str | None = None,
    dev_field: str | None = None,
    dev_filter: str | None = None,
    client_label: str | None = None,
    timezone: str = "America/Sao_Paulo",
    mode: str = "full",
    jira_base_url: str | None = None,
    weekly_highlights: dict[str, str] | None = None,
    attention_points: list[str] | None = None,
) -> dict[str, Any]:
    selected_statuses = statuses or DEFAULT_STATUSES
    discovered = discover_field_ids(client)
    impeditivo_field = impeditivo_field or discovered["impeditivo"]
    dev_field = dev_field or discovered["dev_responsavel"]
    base_url = (jira_base_url or client.base_url).rstrip("/")

    if not parent_label and parent_key:
        try:
            parent_issue = client.get_issue(parent_key, fields=["summary"])
            parent_label = parent_issue.get("fields", {}).get("summary") or parent_key
        except Exception:
            parent_label = parent_key

    project_statuses: list[str] = []
    if project_key:
        try:
            project_statuses = client.get_project_statuses(project_key)
        except Exception:
            project_statuses = []

    resolved_statuses = resolve_statuses(project_statuses, selected_statuses)

    requested_fields = [
        "summary",
        "status",
        "assignee",
        "parent",
        "progress",
        "aggregateprogress",
        "subtasks",
    ]
    if impeditivo_field:
        requested_fields.append(impeditivo_field)
    if dev_field and dev_field not in requested_fields:
        requested_fields.append(dev_field)

    jql = _build_jql(parent_key, resolved_statuses, project_key, space_name)
    issues = client.search_issues(jql, fields=requested_fields)

    cards: list[dict[str, Any]] = []
    issue_aggregate: dict[str, Any] = {}
    issue_subtask_keys: dict[str, list[str]] = {}
    for issue in issues:
        fields = issue.get("fields", {})
        issue_key = issue.get("key", "")
        issue_aggregate[issue_key] = fields.get("aggregateprogress")
        issue_subtask_keys[issue_key] = [
            subtask.get("key")
            for subtask in (fields.get("subtasks") or [])
            if subtask.get("key")
        ]
        cards.append(
            _issue_to_card(
                issue,
                client=client,
                dev_field=dev_field,
                impeditivo_field=impeditivo_field,
                timezone=timezone,
                base_url=base_url,
            )
        )

    if dev_filter:
        dev_normalized = _normalize_text(dev_filter)
        cards = [
            card
            for card in cards
            if _normalize_text(card.get("dev_responsavel", "")) == dev_normalized
        ]

    delivered_cards = _fetch_delivered_cards(
        client,
        parent_key=parent_key,
        project_key=project_key,
        dev_field=dev_field,
        impeditivo_field=impeditivo_field,
        timezone=timezone,
        base_url=base_url,
    )
    if dev_filter:
        dev_normalized = _normalize_text(dev_filter)
        delivered_cards = [
            card
            for card in delivered_cards
            if _normalize_text(card.get("dev_responsavel", "")) == dev_normalized
        ]

    delivered_stats = _summarize_delivered_stats(delivered_cards, timezone=timezone)

    cards.sort(key=lambda card: (_status_sort_key(card["status"]), card["summary"].lower()))
    _attach_card_progress(client, cards, issue_aggregate, issue_subtask_keys)

    total_before_filter = len(cards)
    impeditive_count_all = sum(1 for card in cards if card["impeditivo"] == "Sim")
    all_cards = list(cards)
    if mode == "impeditive_only":
        cards = [card for card in cards if card["impeditivo"] == "Sim"]

    impeditive_count = impeditive_count_all if mode == "full" else len(cards)
    now = _local_now(timezone).strftime("%d/%m/%Y %H:%M")
    report_title = _build_report_title(parent_key, parent_label)
    text = _format_report_markdown(cards, now, impeditive_count, report_title)
    text_html = _format_report_text_rich_html(cards, now, impeditive_count, report_title)
    whatsapp_text = _format_report_whatsapp_text(cards, now, impeditive_count, report_title)
    email_html = build_email_html(
        report_title=report_title,
        generated_at=now,
        total_cards=len(cards),
        impeditive_count=impeditive_count,
        cards=cards,
        kpi_cards=all_cards,
        parent_label=parent_label,
        mode=mode,
        weekly_highlights=weekly_highlights,
        attention_points=attention_points,
    )
    report_html = build_status_report_html(
        report_title=report_title,
        generated_at=now,
        cards=all_cards,
        parent_label=parent_label,
        weekly_highlights=weekly_highlights,
        attention_points=attention_points,
        client_label=client_label or parent_label,
        entregues_mes=int(delivered_stats["entregues_mes"]),
        entregues_total=int(delivered_stats["entregues_total"]),
    )

    return {
        "generated_at": now,
        "mode": mode,
        "parent_key": parent_key,
        "parent_label": parent_label,
        "report_title": report_title,
        "total_cards": len(cards),
        "total_cards_before_filter": total_before_filter,
        "impeditive_count": impeditive_count,
        "jql": jql,
        "cards": cards,
        "delivered_cards": delivered_cards,
        "delivered_stats": delivered_stats,
        "text": text,
        "text_html": text_html,
        "whatsapp_text": whatsapp_text,
        "email_html": email_html,
        "report_html": report_html,
        "email_subject": build_email_subject(
            {
                "parent_key": parent_key,
                "parent_label": parent_label,
                "impeditive_count": impeditive_count,
                "generated_at": now,
                "mode": mode,
            }
        ),
        "report_subject": build_report_subject(
            {
                "parent_key": parent_key,
                "parent_label": parent_label,
                "generated_at": now,
            }
        ),
        "field_mapping": {
            "impeditivo": impeditivo_field,
            "dev_responsavel": dev_field,
        },
    }


def _format_stale_line(card: dict[str, Any]) -> str:
    days = card.get("dias_sem_atualizacao")
    if days is None:
        return ""
    if days == 0:
        return "Atualizado hoje"
    if days == 1:
        return "1 dia sem atualização"
    return f"{days} dias sem atualização"


def _md_escape_inline(text: str) -> str:
    value = str(text or "")
    return value.replace("\\", "\\\\").replace("*", "\\*").replace("#", "\\#").replace("[", "\\[")


def _md_blockquote(text: str) -> str:
    lines = str(text or "").splitlines() or [""]
    return "\n".join(f"> {line}" if line else ">" for line in lines)


def _wa_bold(text: str) -> str:
    return f"*{str(text or '').replace('*', '')}*"


def _format_progress_line(card: dict[str, Any]) -> str:
    progress = card.get("progresso_subtarefas")
    if progress is None:
        return ""
    done = card.get("progresso_subtarefas_concluidas")
    total = card.get("progresso_subtarefas_total")
    if done is not None and total is not None and total > 0:
        return f"- **Progresso subtarefas:** {progress}% ({done}/{total})"
    return f"- **Progresso subtarefas:** {progress}%"


def _format_report_markdown(
    cards: list[dict[str, Any]],
    generated_at: str,
    impeditive_count: int,
    report_title: str,
) -> str:
    lines: list[str] = [
        f"# 📋 {_md_escape_inline(report_title)}",
        "",
        f"🕐 **{_md_escape_inline(generated_at)}**",
        "",
        f"📊 **{len(cards)} card(s)** (🚨 **{impeditive_count}** dos projetos possuem impeditivos)",
        "",
        "---",
        "",
    ]

    current_status: str | None = None
    for card in cards:
        if card["status"] != current_status:
            current_status = card["status"]
            lines.extend([f"## {_md_escape_inline(current_status)}", ""])

        stale_line = _format_stale_line(card)
        progress_line = _format_progress_line(card)
        lines.append(f"### {_md_escape_inline(card['summary'])}")
        lines.append("")
        lines.append(f"- **Dev. Responsável:** {_md_escape_inline(card['dev_responsavel'])}")
        lines.append(f"- **Impeditivo:** {_md_escape_inline(card['impeditivo'])}")
        if stale_line:
            lines.append(f"- {_md_escape_inline(stale_line)}")
        if progress_line:
            lines.append(progress_line)
        lines.extend(
            [
                "",
                "**Última Atualização:**",
                "",
                _md_blockquote(card.get("ultima_atualizacao_exibicao") or card["ultima_atualizacao"]),
                "",
            ]
        )
        if card["ultima_atualizacao_data"]:
            lines.append(f"*{_md_escape_inline(card['ultima_atualizacao_data'])}*")
        lines.extend(["", "---", ""])

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def _format_report_text_rich_html(
    cards: list[dict[str, Any]],
    generated_at: str,
    impeditive_count: int,
    report_title: str,
) -> str:
    blocks: list[str] = [
        "<section class='report-rich'>",
        f"<h1>{_md_escape_inline(report_title)}</h1>",
        f"<p><strong>Gerado em:</strong> {_md_escape_inline(generated_at)}</p>",
        f"<p><strong>Resumo:</strong> {len(cards)} card(s) | {impeditive_count} com impeditivo</p>",
    ]

    current_status: str | None = None
    for card in cards:
        if card["status"] != current_status:
            current_status = card["status"]
            blocks.append(f"<h2>{_md_escape_inline(current_status)}</h2>")

        progress = card.get("progresso_subtarefas")
        done = card.get("progresso_subtarefas_concluidas")
        total = card.get("progresso_subtarefas_total")
        progress_line = ""
        if progress is not None and done is not None and total:
            progress_line = f"{progress}% ({done}/{total})"
        elif progress is not None:
            progress_line = f"{progress}%"

        blocks.extend(
            [
                "<article class='report-rich-card'>",
                f"<h3>{_md_escape_inline(card['summary'])}</h3>",
                f"<p><strong>Responsável:</strong> {_md_escape_inline(card['dev_responsavel'])}</p>",
                f"<p><strong>Impeditivo:</strong> {_md_escape_inline(card['impeditivo'])}</p>",
                f"<p><strong>Etapa:</strong> {_md_escape_inline(card['status'])}</p>",
            ]
        )
        if progress_line:
            blocks.append(f"<p><strong>Progresso subtarefas:</strong> {progress_line}</p>")
        blocks.extend(
            [
                "<p><strong>Última atualização:</strong></p>",
                (
                    f"<blockquote>{_md_escape_inline(card.get('ultima_atualizacao_exibicao') or card['ultima_atualizacao']).replace(chr(10), '<br>')}</blockquote>"
                ),
            ]
        )
        if card["ultima_atualizacao_data"]:
            blocks.append(f"<p><em>{_md_escape_inline(card['ultima_atualizacao_data'])}</em></p>")
        blocks.append("</article>")

    blocks.append("</section>")
    return "\n".join(blocks)


def _format_report_whatsapp_text(
    cards: list[dict[str, Any]],
    generated_at: str,
    impeditive_count: int,
    report_title: str,
) -> str:
    lines: list[str] = [
        f"📋 {report_title}",
        f"🕐 {generated_at}",
        f"📊 {len(cards)} card(s) (🚨 {_wa_bold(f'{impeditive_count} dos projetos possuem impeditivos')} )",
        "",
    ]

    current_status: str | None = None
    for card in cards:
        if card["status"] != current_status:
            if current_status is not None:
                lines.append(_WA_DIVIDER)
            current_status = card["status"]
            lines.extend([_WA_DIVIDER, _wa_bold(current_status), _WA_DIVIDER])

        stale_line = _format_stale_line(card)
        lines.append(_wa_bold(card["summary"]))
        lines.append(f"Dev. Responsável: {card['dev_responsavel']}")
        lines.append(f"🚩 Flag impeditivo: {card['impeditivo']}")
        if stale_line:
            lines.append(stale_line)
        progress = card.get("progresso_subtarefas")
        if progress is not None:
            done = card.get("progresso_subtarefas_concluidas")
            total = card.get("progresso_subtarefas_total")
            if done is not None and total is not None and total > 0:
                lines.append(f"Progresso subtarefas: {progress}% ({done}/{total})")
            else:
                lines.append(f"Progresso subtarefas: {progress}%")
        lines.extend(
            [
                "",
                "Última Atualização:",
                card.get("ultima_atualizacao_exibicao") or card["ultima_atualizacao"],
            ]
        )
        if card["ultima_atualizacao_data"]:
            lines.append(card["ultima_atualizacao_data"])
        lines.extend([_WA_DIVIDER, ""])

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)
