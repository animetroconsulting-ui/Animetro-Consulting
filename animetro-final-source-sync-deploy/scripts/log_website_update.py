#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import google.auth
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DEFAULT_TAB_NAME = "Animetro Website Update Log"
HEADERS = [
    "Date",
    "Page Updated",
    "Section Updated",
    "Change Type",
    "Before",
    "After",
    "Reason for Change",
    "Status",
    "Branch Name",
    "Commit SHA",
    "Pull Request Link",
    "Notes",
]

STRUCTURED_FIELDS = {
    "page updated": "Page Updated",
    "section updated": "Section Updated",
    "change type": "Change Type",
    "before": "Before",
    "after": "After",
    "reason": "Reason for Change",
    "reason for change": "Reason for Change",
    "notes": "Notes",
}


def sheets_service():
    credentials, _ = google.auth.default(scopes=SCOPES)
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def get_spreadsheet_id() -> str:
    spreadsheet_id = (
        os.environ.get("GOOGLE_SHEET_ID", "").strip()
        or os.environ.get("WEBSITE_UPDATE_LOG_SHEET_ID", "").strip()
    )
    if not spreadsheet_id:
        raise RuntimeError("Missing GOOGLE_SHEET_ID environment variable.")
    return spreadsheet_id


def get_tab_name() -> str:
    return os.environ.get("WEBSITE_UPDATE_LOG_TAB_NAME", DEFAULT_TAB_NAME).strip() or DEFAULT_TAB_NAME


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def normalized_date(value: str | None) -> str:
    if not value:
        return today()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        return today()


def event_payload() -> dict[str, Any]:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        return {}
    path = Path(event_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_structured_fields(message: str) -> dict[str, str]:
    fields = {
        "Page Updated": "",
        "Section Updated": "",
        "Change Type": "",
        "Before": "",
        "After": "",
        "Reason for Change": "",
        "Notes": "",
    }
    current_key = ""

    for line in message.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            normalized = key.strip().lstrip("-*").strip().lower()
            mapped_key = STRUCTURED_FIELDS.get(normalized)
            if mapped_key:
                fields[mapped_key] = value.strip()
                current_key = mapped_key
                continue
        if current_key and line.strip():
            fields[current_key] = f"{fields[current_key]}\n{line.strip()}".strip()

    return fields


def has_structured_content(fields: dict[str, str]) -> bool:
    return any(value.strip() for value in fields.values())


def git_changed_files(sha: str) -> list[str]:
    if not sha:
        return []
    commands = [
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
        ["git", "show", "--pretty=", "--name-only", sha],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if files:
            return sorted(set(files))
    return []


def changed_files_from_push(payload: dict[str, Any], sha: str) -> list[str]:
    head_commit = payload.get("head_commit") or {}
    files = []
    for key in ("added", "modified", "removed"):
        files.extend(head_commit.get(key) or [])
    return sorted(set(files)) or git_changed_files(sha)


def github_commit_url(repo: str, sha: str) -> str:
    if not repo or not sha:
        return ""
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    return f"{server_url}/{repo}/commit/{sha}"


def find_pull_request_link(repo: str, sha: str) -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token or not repo or not sha:
        return ""

    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/commits/{sha}/pulls",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            pull_requests = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return ""

    if not pull_requests:
        return ""
    return pull_requests[0].get("html_url", "")


def push_row() -> list[str] | None:
    payload = event_payload()
    if payload.get("ref") and payload.get("ref") != "refs/heads/main":
        return None

    head_commit = payload.get("head_commit") or {}
    sha = os.environ.get("GITHUB_SHA", "").strip() or payload.get("after", "") or head_commit.get("id", "")
    branch_name = os.environ.get("GITHUB_REF_NAME", "").strip() or "main"
    commit_message = head_commit.get("message") or ""
    commit_date = normalized_date(head_commit.get("timestamp"))
    changed_files = changed_files_from_push(payload, sha)
    fields = parse_structured_fields(commit_message)
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    pr_link = find_pull_request_link(repo, sha)
    commit_link = github_commit_url(repo, sha)

    if has_structured_content(fields):
        notes = fields["Notes"]
        if commit_link and not pr_link:
            notes = f"{notes}\nCommit link: {commit_link}".strip()
        return [
            commit_date,
            fields["Page Updated"],
            fields["Section Updated"],
            fields["Change Type"],
            fields["Before"],
            fields["After"],
            fields["Reason for Change"],
            "Confirmed",
            branch_name,
            sha,
            pr_link,
            notes,
        ]

    notes_parts = ["Auto-logged from main branch update"]
    if commit_message:
        notes_parts.append(f"Commit message: {commit_message}")
    if commit_link and not pr_link:
        notes_parts.append(f"Commit link: {commit_link}")

    return [
        commit_date,
        "",
        "\n".join(changed_files),
        "",
        "",
        "",
        "",
        "Confirmed",
        branch_name,
        sha,
        pr_link,
        "\n".join(notes_parts),
    ]


def test_row() -> list[str]:
    return [
        today(),
        "Homepage",
        "Main CTA button",
        "Copy update",
        "Book a Private Consultation",
        "Book a Free Private Consultation",
        "Make the consultation offer clearer and more attractive for parents.",
        "Confirmed",
        os.environ.get("GITHUB_REF_NAME", ""),
        os.environ.get("GITHUB_SHA", ""),
        "",
        "Applied to homepage hero CTA and repeated homepage CTA.",
    ]


def ensure_tab_and_headers(service, spreadsheet_id: str, tab_name: str) -> None:
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = spreadsheet.get("sheets", [])
    tab = next((sheet for sheet in sheets if sheet.get("properties", {}).get("title") == tab_name), None)

    if tab is None:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
        ).execute()

    header_range = f"'{tab_name}'!A1:L1"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=header_range,
    ).execute()
    values = result.get("values", [])
    if not values or values[0] != HEADERS:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=header_range,
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()


def append_row(service, spreadsheet_id: str, tab_name: str, row: list[str]) -> None:
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!A:L",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["push", "test-row"], required=True)
    args = parser.parse_args()

    row = test_row() if args.mode == "test-row" else push_row()
    if row is None:
        print("No confirmed main-branch update to log.")
        return

    service = sheets_service()
    spreadsheet_id = get_spreadsheet_id()
    tab_name = get_tab_name()
    ensure_tab_and_headers(service, spreadsheet_id, tab_name)
    append_row(service, spreadsheet_id, tab_name, row)
    print(f"Logged website update to {tab_name}.")


if __name__ == "__main__":
    main()
