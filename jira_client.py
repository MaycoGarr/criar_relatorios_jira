"""Cliente para a API REST do Jira Cloud."""

from __future__ import annotations

import base64
from typing import Any

import requests


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        self.session.headers.update(
            {
                "Authorization": f"Basic {credentials}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=60)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        response = self.session.post(
            f"{self.base_url}{path}", json=payload, timeout=60
        )
        response.raise_for_status()
        return response.json()

    def test_connection(self) -> dict[str, Any]:
        return self._get("/rest/api/3/myself")

    def get_issue(self, issue_key: str, fields: list[str] | None = None) -> dict[str, Any]:
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        return self._get(f"/rest/api/3/issue/{issue_key}", params)

    def get_fields(self) -> list[dict[str, Any]]:
        return self._get("/rest/api/3/field")

    def get_projects(self) -> list[dict[str, Any]]:
        return self._get("/rest/api/3/project/search", {"maxResults": 100})["values"]

    def get_project_statuses(self, project_key: str) -> list[str]:
        data = self._get(f"/rest/api/3/project/{project_key}/statuses")
        names: list[str] = []
        for item in data:
            for status in item.get("statuses", []):
                name = status.get("name")
                if name and name not in names:
                    names.append(name)
        return names

    def get_project_issue_types(self, project_key: str) -> list[str]:
        data = self._get(f"/rest/api/3/project/{project_key}/statuses")
        names: list[str] = []
        for item in data:
            name = item.get("name")
            if name and name not in names:
                names.append(name)
        return names

    def get_parent_candidates(self, project_key: str) -> list[dict[str, Any]]:
        issue_types = self.get_project_issue_types(project_key)
        parent_types = [
            issue_type
            for issue_type in issue_types
            if issue_type.lower() not in {"sub-task", "subtarefa", "subtarefa", "bug", "task", "tarefa"}
        ]

        if parent_types:
            quoted_types = ", ".join(f'"{issue_type}"' for issue_type in parent_types)
            jql = f'project = "{project_key}" AND issuetype in ({quoted_types}) ORDER BY summary ASC'
        else:
            jql = f'project = "{project_key}" AND parent is EMPTY ORDER BY summary ASC'

        issues = self.search_issues(jql, fields=["summary", "status", "issuetype"])
        candidates: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        for issue in issues:
            key = issue.get("key", "")
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            summary = issue.get("fields", {}).get("summary", "")
            candidates.append(
                {
                    "key": key,
                    "summary": summary,
                    "label": f"{key} — {summary}" if summary else key,
                }
            )

        return candidates

    def get_boards(self) -> list[dict[str, Any]]:
        boards: list[dict[str, Any]] = []
        start_at = 0
        while True:
            data = self._get(
                "/rest/agile/1.0/board",
                {"startAt": start_at, "maxResults": 50},
            )
            boards.extend(data.get("values", []))
            if data.get("isLast", True):
                break
            start_at += data.get("maxResults", 50)
        return boards

    def search_issues(
        self,
        jql: str,
        fields: list[str] | None = None,
        expand: str | None = None,
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        next_page_token: str | None = None

        while True:
            payload: dict[str, Any] = {
                "jql": jql,
                "maxResults": 100,
                "fields": fields or ["summary", "status", "assignee", "parent"],
            }
            if expand:
                payload["expand"] = expand
            if next_page_token:
                payload["nextPageToken"] = next_page_token

            data = self._post("/rest/api/3/search/jql", payload)
            issues.extend(data.get("issues", []))

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return issues

    def get_issue_comments(self, issue_key: str) -> list[dict[str, Any]]:
        data = self._get(f"/rest/api/3/issue/{issue_key}/comment", {"maxResults": 100})
        return data.get("comments", [])

    def get_issue_changelog(self, issue_key: str) -> list[dict[str, Any]]:
        histories: list[dict[str, Any]] = []
        start_at = 0
        while True:
            data = self._get(
                f"/rest/api/3/issue/{issue_key}/changelog",
                {"startAt": start_at, "maxResults": 100},
            )
            histories.extend(data.get("values", []))
            if start_at + data.get("maxResults", 100) >= data.get("total", 0):
                break
            start_at += data.get("maxResults", 100)
        return histories

    def get_subtasks_for_parents(
        self,
        parent_keys: list[str],
        parent_subtask_keys: dict[str, list[str]] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        if not parent_keys:
            return {}

        grouped: dict[str, list[dict[str, Any]]] = {key: [] for key in parent_keys}
        issues_by_key: dict[str, dict[str, Any]] = {}

        quoted = ", ".join(parent_keys)
        jql = f"parent in ({quoted}) ORDER BY key ASC"
        for issue in self.search_issues(jql, fields=["summary", "status", "parent", "progress"]):
            parent = issue.get("fields", {}).get("parent") or {}
            parent_key = parent.get("key")
            issue_key = issue.get("key")
            if parent_key in grouped and issue_key:
                issues_by_key[issue_key] = issue
                grouped[parent_key].append(issue)

        extra_keys: list[str] = []
        for parent_key in parent_keys:
            for subtask_key in (parent_subtask_keys or {}).get(parent_key, []):
                if subtask_key not in issues_by_key:
                    extra_keys.append(subtask_key)

        if extra_keys:
            unique_extra = list(dict.fromkeys(extra_keys))
            quoted_extra = ", ".join(unique_extra)
            jql_extra = f"key in ({quoted_extra}) ORDER BY key ASC"
            for issue in self.search_issues(jql_extra, fields=["summary", "status", "parent", "progress"]):
                issue_key = issue.get("key")
                if not issue_key or issue_key in issues_by_key:
                    continue
                issues_by_key[issue_key] = issue
                parent = issue.get("fields", {}).get("parent") or {}
                parent_key = parent.get("key")
                if parent_key in grouped:
                    grouped[parent_key].append(issue)

        return grouped
