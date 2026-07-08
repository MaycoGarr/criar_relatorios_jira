"""API local para consulta ao Jira e geração de relatórios."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from requests import HTTPError

from credentials_store import (
    create_credential,
    delete_credential,
    get_credential,
    get_credential_with_secret,
    get_default_credential,
    get_default_credential_with_secret,
    import_from_env as import_jira_from_env,
    list_credentials,
    set_default_credential,
    update_credential,
)
from email_sender import send_email
from email_store import (
    create_connection,
    delete_connection,
    get_connection,
    get_connection_with_secret,
    get_default_connection,
    get_default_connection_with_secret,
    import_from_env as import_email_from_env,
    list_connections,
    set_default_connection,
    update_connection,
)
from filter_store import (
    create_preset,
    delete_preset,
    get_default_preset,
    get_preset,
    import_defaults as import_filter_defaults,
    list_presets,
    set_default_preset,
    update_preset,
)
from jira_client import JiraClient
from report_builder import DEFAULT_STATUSES, build_email_subject, build_report, build_report_subject, discover_field_ids, get_board_people, resolve_statuses

load_dotenv()

app = Flask(__name__, static_folder="static")
CORS(app)

import_jira_from_env()
import_email_from_env()
import_filter_defaults()


def _client_from_credential_id(credential_id: str | None) -> JiraClient:
    credential = (
        get_credential_with_secret(credential_id)
        if credential_id
        else get_default_credential_with_secret()
    )
    if not credential:
        raise ValueError("Nenhuma conexão Jira cadastrada. Crie uma conexão para continuar.")

    return JiraClient(
        credential["base_url"],
        credential["email"],
        credential["api_token"],
    )


def _client_from_payload(payload: dict[str, Any]) -> JiraClient:
    credential_id = payload.get("credential_id")
    if credential_id:
        return _client_from_credential_id(credential_id)

    base_url = payload.get("base_url") or os.getenv("JIRA_BASE_URL", "")
    email = payload.get("email") or os.getenv("JIRA_EMAIL", "")
    token = payload.get("api_token") or os.getenv("JIRA_API_TOKEN", "")

    if base_url and email and token:
        return JiraClient(base_url, email, token)

    return _client_from_credential_id(None)


def _email_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    connection_id = payload.get("email_connection_id")
    connection = (
        get_connection_with_secret(connection_id)
        if connection_id
        else get_default_connection_with_secret()
    )
    if not connection:
        raise ValueError("Nenhuma conexão de e-mail cadastrada. Crie uma conexão SMTP.")
    return connection


def _error_response(error: Exception, status_code: int = 400):
    message = str(error)
    details: Any = None
    if isinstance(error, HTTPError) and error.response is not None:
        try:
            details = error.response.json()
            message = (
                details.get("errorMessages", [message])[0]
                if details.get("errorMessages")
                else message
            )
        except ValueError:
            details = error.response.text
    return jsonify({"error": message, "details": details}), status_code


def _build_filter_options(
    client: JiraClient, project_key: str, preferred_parent_key: str | None = None
) -> dict[str, Any]:
    fields = client.get_fields()
    projects = client.get_projects()
    discovered = discover_field_ids(client)
    parent_cards = client.get_parent_candidates(project_key)
    if preferred_parent_key and not any(
        card["key"] == preferred_parent_key for card in parent_cards
    ):
        try:
            issue = client.get_issue(preferred_parent_key, fields=["summary"])
            summary = issue.get("fields", {}).get("summary", "")
            parent_cards.insert(
                0,
                {
                    "key": preferred_parent_key,
                    "summary": summary,
                    "label": f"{preferred_parent_key} — {summary}" if summary else preferred_parent_key,
                },
            )
        except HTTPError:
            pass

    project_statuses: list[str] = []
    try:
        project_statuses = client.get_project_statuses(project_key)
    except HTTPError:
        project_statuses = []

    resolved_defaults = resolve_statuses(project_statuses, DEFAULT_STATUSES)
    preferred_parent = preferred_parent_key or (parent_cards[0]["key"] if parent_cards else None)
    board_people: list[str] = []
    if preferred_parent:
        try:
            board_people = get_board_people(
                client,
                parent_key=preferred_parent,
                project_key=project_key,
                dev_field=discovered.get("dev_responsavel"),
            )
        except HTTPError:
            board_people = []

    return {
        "fields": [
            {"id": field["id"], "name": field.get("name", "")}
            for field in fields
            if field.get("custom", False)
        ],
        "projects": [
            {"key": project["key"], "name": project.get("name", "")}
            for project in projects
        ],
        "parent_cards": parent_cards,
        "discovered_fields": discovered,
        "default_statuses": resolved_defaults or DEFAULT_STATUSES,
        "project_statuses": project_statuses,
        "board_people": board_people,
    }


def _parse_attention_points(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [line.strip() for line in str(value).splitlines() if line.strip()]


def _parse_weekly_highlights(payload: dict[str, Any]) -> dict[str, str] | None:
    highlights = payload.get("weekly_highlights") or {}
    positive = str(highlights.get("positive") or payload.get("destaque_positivo") or "").strip()
    negative = str(highlights.get("negative") or payload.get("destaque_negativo") or "").strip()
    if not positive and not negative:
        return None
    return {"positive": positive, "negative": negative}


def _report_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    client = _client_from_payload(payload)
    parent_key = payload.get("parent_key", "GERAL4AT-17")
    parent_label = payload.get("parent_label")
    mode = payload.get("mode", "full")

    if not parent_label:
        selected = next(
            (
                card
                for card in payload.get("parent_cards", [])
                if card.get("key") == parent_key
            ),
            None,
        )
        if selected:
            parent_label = selected.get("summary")

    return build_report(
        client,
        parent_key=parent_key,
        parent_label=parent_label,
        client_label=payload.get("client_label"),
        project_key=payload.get("project_key") or None,
        space_name=payload.get("space_name") or None,
        statuses=payload.get("statuses") or DEFAULT_STATUSES,
        impeditivo_field=payload.get("impeditivo_field") or None,
        dev_field=payload.get("dev_field") or None,
        dev_filter=payload.get("dev_filter") or None,
        mode=mode,
        jira_base_url=client.base_url,
        weekly_highlights=_parse_weekly_highlights(payload),
        attention_points=_parse_attention_points(payload.get("attention_points") or payload.get("pontos_atencao")),
    )


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/defaults")
def defaults():
    default_credential = get_default_credential()
    default_email = get_default_connection()
    default_filter = get_default_preset()
    default_parent = default_filter["parent_key"] if default_filter else "GERAL4AT-17"

    return jsonify(
        {
            "credential": default_credential,
            "email_connection": default_email,
            "filter_preset": default_filter,
            "parent_key": default_parent,
            "space_name": default_filter["space_name"] if default_filter else "4AT - Geral",
            "project_key": default_filter["project_key"] if default_filter else "GERAL4AT",
            "statuses": default_filter["statuses"] if default_filter else DEFAULT_STATUSES,
            "report_mode": default_filter["report_mode"] if default_filter else "full",
        }
    )


@app.get("/api/filter-presets")
def filter_presets_list():
    return jsonify({"presets": list_presets()})


@app.get("/api/filter-presets/<preset_id>")
def filter_presets_get(preset_id: str):
    preset = get_preset(preset_id)
    if not preset:
        return jsonify({"error": "Filtro não encontrado."}), 404
    return jsonify(preset)


@app.post("/api/filter-presets")
def filter_presets_create():
    try:
        payload = request.get_json(silent=True) or {}
        preset = create_preset(payload)
        return jsonify(preset), 201
    except Exception as error:
        return _error_response(error)


@app.put("/api/filter-presets/<preset_id>")
def filter_presets_update(preset_id: str):
    try:
        payload = request.get_json(silent=True) or {}
        preset = update_preset(preset_id, payload)
        return jsonify(preset)
    except Exception as error:
        return _error_response(error, 404 if "não encontrado" in str(error) else 400)


@app.delete("/api/filter-presets/<preset_id>")
def filter_presets_delete(preset_id: str):
    try:
        delete_preset(preset_id)
        return jsonify({"ok": True})
    except Exception as error:
        return _error_response(error, 404 if "não encontrado" in str(error) else 400)


@app.post("/api/filter-presets/<preset_id>/set-default")
def filter_presets_set_default(preset_id: str):
    try:
        preset = set_default_preset(preset_id)
        return jsonify(preset)
    except Exception as error:
        return _error_response(error, 404 if "não encontrado" in str(error) else 400)


@app.get("/api/credentials")
def credentials_list():
    return jsonify({"credentials": list_credentials()})


@app.get("/api/credentials/<credential_id>")
def credentials_get(credential_id: str):
    credential = get_credential(credential_id, include_token=True)
    if not credential:
        return jsonify({"error": "Credencial não encontrada."}), 404
    return jsonify(credential)


@app.post("/api/credentials")
def credentials_create():
    try:
        payload = request.get_json(silent=True) or {}
        credential = create_credential(payload)
        return jsonify(credential), 201
    except Exception as error:
        return _error_response(error)


@app.put("/api/credentials/<credential_id>")
def credentials_update(credential_id: str):
    try:
        payload = request.get_json(silent=True) or {}
        credential = update_credential(credential_id, payload)
        return jsonify(credential)
    except Exception as error:
        return _error_response(error, 404 if "não encontrada" in str(error) else 400)


@app.delete("/api/credentials/<credential_id>")
def credentials_delete(credential_id: str):
    try:
        delete_credential(credential_id)
        return jsonify({"ok": True})
    except Exception as error:
        return _error_response(error, 404 if "não encontrada" in str(error) else 400)


@app.post("/api/credentials/<credential_id>/set-default")
def credentials_set_default(credential_id: str):
    try:
        credential = set_default_credential(credential_id)
        return jsonify(credential)
    except Exception as error:
        return _error_response(error, 404 if "não encontrada" in str(error) else 400)


@app.get("/api/email-connections")
def email_connections_list():
    return jsonify({"connections": list_connections()})


@app.get("/api/email-connections/<connection_id>")
def email_connections_get(connection_id: str):
    connection = get_connection(connection_id, include_password=True)
    if not connection:
        return jsonify({"error": "Conexão de e-mail não encontrada."}), 404
    return jsonify(connection)


@app.post("/api/email-connections")
def email_connections_create():
    try:
        payload = request.get_json(silent=True) or {}
        connection = create_connection(payload)
        return jsonify(connection), 201
    except Exception as error:
        return _error_response(error)


@app.put("/api/email-connections/<connection_id>")
def email_connections_update(connection_id: str):
    try:
        payload = request.get_json(silent=True) or {}
        connection = update_connection(connection_id, payload)
        return jsonify(connection)
    except Exception as error:
        return _error_response(error, 404 if "não encontrada" in str(error) else 400)


@app.delete("/api/email-connections/<connection_id>")
def email_connections_delete(connection_id: str):
    try:
        delete_connection(connection_id)
        return jsonify({"ok": True})
    except Exception as error:
        return _error_response(error, 404 if "não encontrada" in str(error) else 400)


@app.post("/api/email-connections/<connection_id>/set-default")
def email_connections_set_default(connection_id: str):
    try:
        connection = set_default_connection(connection_id)
        return jsonify(connection)
    except Exception as error:
        return _error_response(error, 404 if "não encontrada" in str(error) else 400)


@app.post("/api/email-connections/<connection_id>/test")
def email_connections_test(connection_id: str):
    try:
        payload = request.get_json(silent=True) or {}
        connection = get_connection_with_secret(connection_id)
        if not connection:
            return jsonify({"error": "Conexão de e-mail não encontrada."}), 404

        recipients = payload.get("recipients") or connection.get("default_recipients") or []
        if not recipients:
            raise ValueError("Informe destinatários para o teste de envio.")

        subject = "Teste — Relatório Jira UISA"
        text_body = "Este é um e-mail de teste do sistema de relatórios Jira."
        html_body = "<p>Este é um <strong>e-mail de teste</strong> do sistema de relatórios Jira.</p>"
        result = send_email(
            connection,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            recipients=recipients,
        )
        return jsonify(result)
    except Exception as error:
        return _error_response(error)


@app.post("/api/test-connection")
def test_connection():
    try:
        payload = request.get_json(silent=True) or {}
        client = _client_from_payload(payload)
        user = client.test_connection()
        return jsonify(
            {
                "ok": True,
                "display_name": user.get("displayName"),
                "email": user.get("emailAddress"),
            }
        )
    except Exception as error:
        return _error_response(error, 401 if isinstance(error, HTTPError) else 400)


@app.post("/api/filter-options")
def filter_options():
    try:
        payload = request.get_json(silent=True) or {}
        client = _client_from_payload(payload)
        project_key = payload.get("project_key") or "GERAL4AT"
        preferred_parent_key = payload.get("preferred_parent_key") or payload.get("parent_key")
        return jsonify(_build_filter_options(client, project_key, preferred_parent_key))
    except Exception as error:
        return _error_response(error)


@app.post("/api/report")
def report():
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify(_report_from_payload(payload))
    except Exception as error:
        return _error_response(error)


@app.post("/api/report/send-email")
def report_send_email():
    try:
        payload = request.get_json(silent=True) or {}
        mode = payload.get("mode", "impeditive_only")
        skip_if_empty = bool(payload.get("skip_if_empty", True))
        email_view = payload.get("email_view", "executivo")

        report_data = _report_from_payload({**payload, "mode": mode})

        should_skip = (
            mode == "impeditive_only"
            and report_data["impeditive_count"] == 0
            and skip_if_empty
            and email_view in {"executivo", "both"}
        )
        if should_skip:
            return jsonify(
                {
                    "ok": False,
                    "skipped": True,
                    "message": "Nenhum impeditivo para notificar.",
                    "report": report_data,
                }
            )

        connection = _email_from_payload(payload)
        recipients = payload.get("recipients") or connection.get("default_recipients") or []
        text_body = report_data["text"]
        sends: list[dict[str, Any]] = []

        if email_view in {"executivo", "both"}:
            subject = payload.get("subject") or report_data.get("email_subject") or build_email_subject(report_data)
            sends.append(
                send_email(
                    connection,
                    subject=subject,
                    text_body=text_body,
                    html_body=report_data.get("email_html") or report_data["text_html"],
                    recipients=recipients,
                )
            )

        if email_view in {"report", "both"}:
            subject = (
                payload.get("report_subject")
                or report_data.get("report_subject")
                or build_report_subject(report_data)
            )
            sends.append(
                send_email(
                    connection,
                    subject=subject,
                    text_body=text_body,
                    html_body=report_data.get("report_html") or report_data["text_html"],
                    recipients=recipients,
                )
            )

        if not sends:
            raise ValueError("Selecione um layout de e-mail válido (executivo, report ou ambos).")

        result = sends[0] if len(sends) == 1 else {"ok": True, "recipients": recipients, "sent_count": len(sends)}
        return jsonify({**result, "report": report_data, "email_view": email_view, "sends": sends})
    except Exception as error:
        return _error_response(error)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
