"""CLI para envio agendado de relatórios por e-mail."""

from __future__ import annotations

import argparse

from credentials_store import get_default_credential_with_secret
from email_sender import send_email
from email_store import get_default_connection_with_secret
from jira_client import JiraClient
from report_builder import DEFAULT_STATUSES, build_report, build_report_subject


def main() -> int:
    parser = argparse.ArgumentParser(description="Envia relatório Jira por e-mail.")
    parser.add_argument(
        "--mode",
        choices=["full", "impeditive_only"],
        default="impeditive_only",
        help="Modo do relatório",
    )
    parser.add_argument("--parent-key", default="GERAL4AT-17")
    parser.add_argument("--project-key", default="GERAL4AT")
    parser.add_argument(
        "--email-view",
        choices=["executivo", "report", "both"],
        default="executivo",
        help="Layout HTML do e-mail",
    )
    parser.add_argument("--skip-if-empty", action="store_true", default=True)
    args = parser.parse_args()

    jira_cred = get_default_credential_with_secret()
    email_conn = get_default_connection_with_secret()
    if not jira_cred:
        raise SystemExit("Nenhuma conexão Jira padrão cadastrada.")
    if not email_conn:
        raise SystemExit("Nenhuma conexão SMTP padrão cadastrada.")

    client = JiraClient(jira_cred["base_url"], jira_cred["email"], jira_cred["api_token"])
    report = build_report(
        client,
        parent_key=args.parent_key,
        project_key=args.project_key,
        statuses=DEFAULT_STATUSES,
        mode=args.mode,
        jira_base_url=jira_cred["base_url"],
    )

    if (
        args.mode == "impeditive_only"
        and report["impeditive_count"] == 0
        and args.skip_if_empty
        and args.email_view in {"executivo", "both"}
    ):
        print("Nenhum impeditivo para notificar.")
        return 0

    recipients = email_conn.get("default_recipients") or []
    sends = 0
    if args.email_view in {"executivo", "both"}:
        send_email(
            email_conn,
            subject=report["email_subject"],
            text_body=report["text"],
            html_body=report.get("email_html") or report["text_html"],
            recipients=recipients,
        )
        sends += 1
    if args.email_view in {"report", "both"}:
        send_email(
            email_conn,
            subject=report.get("report_subject") or build_report_subject(report),
            text_body=report["text"],
            html_body=report.get("report_html") or report["text_html"],
            recipients=recipients,
        )
        sends += 1
    print(f"{sends} e-mail(s) enviado(s) para: {', '.join(recipients)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
