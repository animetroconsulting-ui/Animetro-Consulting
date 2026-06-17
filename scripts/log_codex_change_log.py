#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import google.auth
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DEFAULT_TAB_NAME = "Codex Change Log"
HEADERS = ["Date/Time", "File Changed", "Section/Page", "Old Text", "New Text", "Commit SHA", "Changed By"]
CONTENT_FILE_PATTERNS = (
    re.compile(r"^(en|zh)(/.*)?/index\.html$"),
    re.compile(r"^index\.html$"),
    re.compile(r"^content/.*\.csv$"),
    re.compile(r"^assets/contact\.js$"),
)


def sheets_service():
    credentials, _ = google.auth.default(scopes=SCOPES)
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def spreadsheet_id() -> str:
    value = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not value:
        raise RuntimeError("Missing GOOGLE_SHEET_ID environment variable.")
    return value


def tab_name() -> str:
    return os.environ.get("CODEX_CHANGE_LOG_TAB_NAME", DEFAULT_TAB_NAME).strip() or DEFAULT_TAB_NAME


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def event_payload() -> dict[str, Any]:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        return {}
    path = Path(event_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def is_content_file(path: str) -> bool:
    return any(pattern.match(path) for pattern in CONTENT_FILE_PATTERNS)


def section_page_from_path(path: str) -> str:
    parts = Path(path).parts
    if not parts:
        return ""
    if parts[0] in {"en", "zh"}:
        language = "English" if parts[0] == "en" else "Chinese"
        if len(parts) == 2:
            return f"{language} home"
        return f"{language} / {'/'.join(parts[1:-1])}"
    if parts[0] == "content":
        return "Content source CSV"
    if path == "index.html":
        return "Language landing page"
    if path == "assets/contact.js":
        return "Contact form behavior/content"
    return ""


def changed_files_from_git(sha: str) -> list[str]:
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


def changed_files_from_event(payload: dict[str, Any], sha: str) -> list[str]:
    head_commit = payload.get("head_commit") or {}
    files = []
    for key in ("added", "modified", "removed"):
        files.extend(head_commit.get(key) or [])
    return sorted(set(files)) or changed_files_from_git(sha)


def trim_cell(value: str, limit: int = 4500) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 20].rstrip() + "\n...[truncated]"


def changed_text_for_file(sha: str, path: str) -> tuple[str, str]:
    if not sha:
        return "", ""
    try:
        result = subprocess.run(
            ["git", "diff", "--unified=0", f"{sha}^", sha, "--", path],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "", ""

    old_lines = []
    new_lines = []
    for line in result.stdout.splitlines():
        if not line or line.startswith(("---", "+++", "@@")):
            continue
        if line.startswith("-"):
            old_lines.append(line[1:].strip())
        elif line.startswith("+"):
            new_lines.append(line[1:].strip())
    return trim_cell("\n".join(old_lines)), trim_cell("\n".join(new_lines))


def rows_for_push() -> list[list[str]]:
    payload = event_payload()
    if payload.get("ref") and payload.get("ref") != "refs/heads/main":
        return []

    head_commit = payload.get("head_commit") or {}
    sha = os.environ.get("GITHUB_SHA", "").strip() or payload.get("after", "") or head_commit.get("id", "")
    files = [path for path in changed_files_from_event(payload, sha) if is_content_file(path)]
    timestamp = now_iso()
    return [
        [timestamp, path, section_page_from_path(path), *changed_text_for_file(sha, path), sha, "Codex"]
        for path in files
    ]


def test_row() -> list[str]:
    return [
        now_iso(),
        "en/index.html",
        "English home",
        "Old website text example",
        "New website text example",
        os.environ.get("GITHUB_SHA", ""),
        "Codex",
    ]


def column_letter(count: int) -> str:
    letters = ""
    while count:
        count, remainder = divmod(count - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def ensure_tab_and_headers(service, sheet_id: str, name: str) -> None:
    spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheets = spreadsheet.get("sheets", [])
    tab = next((sheet for sheet in sheets if sheet.get("properties", {}).get("title") == name), None)
    if tab is None:
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": name}}}]},
        ).execute()

    last_column = column_letter(len(HEADERS))
    header_range = f"'{name}'!A1:{last_column}1"
    result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=header_range).execute()
    values = result.get("values", [])
    if not values or values[0] != HEADERS:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=header_range,
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()


def append_rows(service, sheet_id: str, name: str, rows: list[list[str]]) -> None:
    if not rows:
        return
    last_column = column_letter(len(HEADERS))
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"'{name}'!A:{last_column}",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()


def main() -> None:
    mode = os.environ.get("CODEX_CHANGE_LOG_MODE", "push").strip()
    rows = [test_row()] if mode == "test" else rows_for_push()
    if not rows:
        print("No direct website content file changes to log for review.")
        return

    service = sheets_service()
    sheet_id = spreadsheet_id()
    name = tab_name()
    ensure_tab_and_headers(service, sheet_id, name)
    append_rows(service, sheet_id, name, rows)
    print(f"Logged {len(rows)} direct content change row(s) to {name}.")


if __name__ == "__main__":
    main()
