#!/usr/bin/env python3
from __future__ import annotations

import csv
import base64
import html
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "website-content.csv"
SERVICE_IMAGES = ROOT / "content" / "service-images.csv"
SERVICES_JSON = ROOT / "content" / "services.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]
DEFAULT_SHEET_TAB_NAME = "Website Copy"
SERVICE_IMAGES_TAB_NAME = "Website Images"
CODEX_CHANGE_LOG_TAB_NAME = "Codex Change Log"
SERVICE_IMAGE_HEADERS = [
    "service_id",
    "image_url",
    "image_alt",
    "image_purpose",
    "image_status",
    "image_file_name",
    "drive_link",
    "live_image_rule",
    "recommended_action",
    "source_section",
]
CODEX_CHANGE_LOG_HEADERS = [
    "Date/Time",
    "File Changed",
    "Section/Page",
    "Old Text",
    "New Text",
    "Commit SHA",
    "Changed By",
    "Action Needed",
]
GENERATED_CONTENT_PATTERNS = (
    re.compile(r"^(en|zh)(/.*)?/index\.html$"),
    re.compile(r"^index\.html$"),
    re.compile(r"^content/(website-content|service-images)\.csv$"),
    re.compile(r"^content/services\.json$"),
    re.compile(r"^assets/contact\.js$"),
)

SERVICE_IMAGE_SECTION_IDS = {
    "Education Strategy": "strategic-planning",
    "Prep School Admissions": "elite-private-school",
    "School Visit & Interview Preparation": "school-visit-interview",
    "University Admissions": "university-application",
    "GPA Management / Academic Skills": "gpa-management",
    "GPA Management": "gpa-management",
    "STEAM Pathway / Enrichment": "steam-pathway",
    "Student Athlete Planning": "student-athlete",
    "Neurodiversity Support": "gifted-diverse-learning",
    "Mental Health Support": "mental-health-support",
    "Guardianship / Student Care": "short-term-guardianship",
}

SERVICE_IMAGE_ALT = {
    "strategic-planning": {"en": "Education strategy consultation", "zh": "學術策略與教育路徑規劃諮詢"},
    "elite-private-school": {"en": "School admissions consulting", "zh": "學校申請諮詢"},
    "school-visit-interview": {"en": "School visit and interview preparation", "zh": "訪校與面試準備"},
    "university-application": {"en": "University application consulting", "zh": "大學申請諮詢"},
    "gpa-management": {"en": "GPA management and academic planning", "zh": "GPA 管理與學術規劃"},
    "steam-pathway": {"en": "STEAM development and enrichment", "zh": "STEAM 發展與拓展"},
    "student-athlete": {"en": "Student-athlete planning support", "zh": "學生運動員規劃支持"},
    "gifted-diverse-learning": {
        "en": "Gifted, high-potential, and neurodiverse learner support",
        "zh": "高智商、高潛能與多元神經譜系學生支持",
    },
    "mental-health-support": {"en": "Student mental health support", "zh": "學生心理健康支持"},
    "short-term-guardianship": {"en": "Short-term guardianship and student care", "zh": "短期監護與學生照顧"},
}

SERVICE_PLACEHOLDER_IMAGE = (
    "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%201200%20720'%3E"
    "%3Crect%20width='1200'%20height='720'%20fill='%23f6f0e6'/%3E"
    "%3Crect%20x='60'%20y='60'%20width='1080'%20height='600'%20rx='24'%20fill='%23fffdf8'%20stroke='%23e7ddcf'%20stroke-width='4'/%3E"
    "%3Ctext%20x='600'%20y='360'%20text-anchor='middle'%20font-family='Arial,sans-serif'%20font-size='42'%20fill='%235d6674'%3EService%20image%20pending%3C/text%3E"
    "%3C/svg%3E"
)

SERVICE_CONTENT_CONFIG = [
    {
        "service_id": "strategic-planning",
        "title_key": "service_education_strategy_title",
        "subtitle_key": "education_strategy_subtitle",
        "description_key": "education_strategy_desc",
        "point_prefix": "education_strategy_point_",
        "max_points": 4,
    },
    {
        "service_id": "elite-private-school",
        "title_key": "service_prep_title",
        "subtitle_key": "prep_subtitle",
        "description_key": "prep_desc",
        "point_prefix": "prep_point_",
        "max_points": 4,
    },
    {
        "service_id": "school-visit-interview",
        "title_key": "school_visit_title",
        "subtitle_key": "school_visit_subtitle",
        "description_key": "school_visit_desc",
        "point_prefix": "school_visit_point_",
        "max_points": 6,
    },
    {
        "service_id": "university-application",
        "title_key": "service_university_title",
        "subtitle_key": "university_subtitle",
        "description_key": "university_desc",
        "point_prefix": "university_point_",
        "max_points": 4,
        "subsections": [
            {
                "title_key": "university_language_training_title",
                "description_key": "university_language_training_desc",
                "point_prefix": "university_language_training_point_",
                "max_points": 4,
            }
        ],
    },
    {
        "service_id": "gpa-management",
        "title_key": "service_gpa_title",
        "subtitle_key": "gpa_subtitle",
        "description_key": "gpa_desc",
        "point_prefix": "gpa_point_",
        "max_points": 4,
    },
    {
        "service_id": "steam-pathway",
        "title_key": "steam_title",
        "subtitle_key": "steam_subtitle",
        "description_key": "steam_desc",
        "point_prefix": "steam_point_",
        "max_points": 4,
    },
    {
        "service_id": "student-athlete",
        "title_key": "athlete_title",
        "subtitle_key": "athlete_subtitle",
        "description_key": "athlete_desc",
        "point_prefix": "athlete_point_",
        "max_points": 4,
    },
    {
        "service_id": "gifted-diverse-learning",
        "title_key": "gifted_title",
        "subtitle_key": "gifted_subtitle",
        "description_key": "gifted_desc",
        "point_prefix": "gifted_point_",
        "max_points": 4,
    },
    {
        "service_id": "mental-health-support",
        "title_key": "mental_health_title",
        "subtitle_key": "mental_health_subtitle",
        "description_key": "mental_health_desc",
        "point_prefix": "mental_health_point_",
        "max_points": 4,
    },
    {
        "service_id": "short-term-guardianship",
        "title_key": "guardianship_title",
        "subtitle_key": "guardianship_subtitle",
        "description_key": "guardianship_desc",
        "point_prefix": "guardianship_point_",
        "max_points": 6,
    },
]


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def load_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with CONTENT.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for raw in reader:
            if len(raw) < 6:
                continue
            if raw[0] == "No":
                continue
            if raw[0] == "Page":
                continue

            if raw[0].strip().isdigit() or (raw[0] == "" and len(raw) > 10 and raw[10] in ("Approved", "Draft", "Pending", "")):
                page = raw[1] if len(raw) > 1 else ""
                section = raw[2] if len(raw) > 2 else ""
                key = raw[3] if len(raw) > 3 else ""
                en = raw[4] if len(raw) > 4 else ""
                zh = raw[5] if len(raw) > 5 else ""
                section_id = raw[6] if len(raw) > 6 else ""
                button = raw[7] if len(raw) > 7 else ""
                link = raw[8] if len(raw) > 8 else ""
                image = raw[9] if len(raw) > 9 else ""
                status = raw[10] if len(raw) > 10 else ""
            else:
                page, section, key, en, zh = raw[:5]
                section_id = raw[5] if len(raw) > 5 else ""
                button = raw[6] if len(raw) > 6 else ""
                link = raw[7] if len(raw) > 7 else ""
                image = raw[8] if len(raw) > 8 else ""
                status = raw[9] if len(raw) > 9 else ""

            if key in ("Key", "Content Key", ""):
                continue
            rows[key] = {
                "page": page,
                "section": section,
                "en": en,
                "zh": zh,
                "section_id": section_id,
                "button": button,
                "status": status,
                "link": link,
                "image": image,
            }
    return rows


ROWS: dict[str, dict[str, str]] = {}
SERVICE_IMAGE_ROWS: dict[str, dict[str, str]] = {}


def normalize_service_image_values(values: list[list[str]]) -> list[dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    for raw in values:
        if len(raw) < 8 or raw[0] != "Services":
            continue

        source_section = raw[3].strip() if len(raw) > 3 else ""
        service_id = SERVICE_IMAGE_SECTION_IDS.get(source_section)
        if not service_id:
            continue

        image_file_name = (raw[4] if len(raw) > 4 else "").strip()
        if not image_file_name:
            continue

        drive_link = (raw[5] if len(raw) > 5 else "").strip()
        recommended_action = (raw[6] if len(raw) > 6 else "").strip()
        live_image_rule = (raw[7] if len(raw) > 7 else "").strip() or "Do not replace existing live image"
        notes = (raw[8] if len(raw) > 8 else "").strip()
        image_status = "Optional / backup" if re.search(r"optional|backup", recommended_action, re.I) else "In Progress"

        normalized[service_id] = {
            "service_id": service_id,
            "image_url": f"/assets/images/services/{image_file_name}",
            "image_alt": SERVICE_IMAGE_ALT.get(service_id, {}).get("en", source_section),
            "image_purpose": notes or f"Service page visual for {source_section}",
            "image_status": image_status,
            "image_file_name": image_file_name,
            "drive_link": drive_link,
            "live_image_rule": live_image_rule,
            "recommended_action": recommended_action,
            "source_section": source_section,
        }
    return [normalized[key] for key in sorted(normalized)]


def write_service_images_csv(rows: list[dict[str, str]]) -> None:
    SERVICE_IMAGES.parent.mkdir(parents=True, exist_ok=True)
    with SERVICE_IMAGES.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SERVICE_IMAGE_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in SERVICE_IMAGE_HEADERS})


def load_service_images() -> dict[str, dict[str, str]]:
    if not SERVICE_IMAGES.exists():
        return {}
    with SERVICE_IMAGES.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            service_id = (row.get("service_id") or "").strip()
            if service_id:
                rows[service_id] = {header: (row.get(header) or "").strip() for header in SERVICE_IMAGE_HEADERS}
    return rows


def localized_value(key: str) -> dict[str, str]:
    row = ROWS.get(key, {})
    return {
        "en": row.get("en", ""),
        "zh": row.get("zh", ""),
    }


def localized_points(prefix: str, max_points: int) -> dict[str, list[str]]:
    points = {"en": [], "zh": []}
    for i in range(1, max_points + 1):
        value = localized_value(f"{prefix}{i}")
        for lang in ("en", "zh"):
            if value[lang]:
                points[lang].append(value[lang])
    return points


def service_image_data(service_id: str) -> dict[str, str]:
    row = SERVICE_IMAGE_ROWS.get(service_id, {})
    image_url = row.get("image_url", "")
    image_file_name = row.get("image_file_name") or Path(image_url).name
    local_image = ROOT / image_url.lstrip("/") if image_url.startswith("/") else None
    if not image_url or (local_image is not None and not local_image.exists()):
        image_url = SERVICE_PLACEHOLDER_IMAGE
        image_file_name = image_file_name or "service-image-pending.svg"

    return {
        "image_url": image_url,
        "image_alt": row.get("image_alt", ""),
        "image_purpose": row.get("image_purpose") or f"Service page visual for {service_id}",
        "image_status": row.get("image_status") or "In Progress",
        "image_file_name": image_file_name,
        "drive_link": row.get("drive_link", ""),
        "live_image_rule": row.get("live_image_rule") or "Do not replace existing live image",
        "recommended_action": row.get("recommended_action", ""),
        "source_section": row.get("source_section", ""),
        "is_placeholder": "true" if image_url == SERVICE_PLACEHOLDER_IMAGE else "false",
    }


def build_services_data() -> list[dict[str, object]]:
    services: list[dict[str, object]] = []
    for config in SERVICE_CONTENT_CONFIG:
        title = localized_value(config["title_key"])
        description = localized_value(config["description_key"])
        if not title["en"] and not title["zh"] and not description["en"] and not description["zh"]:
            continue

        subsections = []
        for subsection_config in config.get("subsections", []):
            subsection = {
                "title": localized_value(subsection_config["title_key"]),
                "description": localized_value(subsection_config["description_key"]),
                "points": localized_points(subsection_config["point_prefix"], subsection_config["max_points"]),
            }
            if subsection["title"]["en"] or subsection["title"]["zh"] or subsection["description"]["en"] or subsection["description"]["zh"]:
                subsections.append(subsection)

        services.append(
            {
                "service_id": config["service_id"],
                "title": title,
                "subtitle": localized_value(config["subtitle_key"]),
                "description": description,
                "points": localized_points(config["point_prefix"], config["max_points"]),
                "image": service_image_data(config["service_id"]),
                "subsections": subsections,
            }
        )
    return services


def write_services_json() -> None:
    SERVICES_JSON.write_text(
        json.dumps(
            {
                "source": {
                    "website_content": "content/website-content.csv",
                    "service_images": "content/service-images.csv",
                    "google_sheet_tabs": [DEFAULT_SHEET_TAB_NAME, SERVICE_IMAGES_TAB_NAME],
                },
                "status": "In Progress",
                "services": build_services_data(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_services_data() -> list[dict[str, object]]:
    if not SERVICES_JSON.exists():
        return build_services_data()
    data = json.loads(SERVICES_JSON.read_text(encoding="utf-8"))
    return data.get("services", [])


def load_service_account_info() -> dict:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError("Missing GOOGLE_SERVICE_ACCOUNT_JSON environment variable.")

    if raw.startswith("{"):
        return json.loads(raw)

    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON must be service-account JSON or base64 JSON.") from exc


def has_google_auth_config() -> bool:
    return bool(
        os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        or os.environ.get("CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE", "").strip()
    )


def sheets_service():
    return google_service("sheets", "v4")


def drive_service():
    return google_service("drive", "v3")


def google_service(api_name: str, api_version: str):
    from googleapiclient.discovery import build

    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"):
        import google.auth

        credentials, _ = google.auth.default(scopes=SCOPES)
    else:
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_info(
            load_service_account_info(),
            scopes=SCOPES,
        )
    return build(api_name, api_version, credentials=credentials, cache_discovery=False)


def get_google_sheet_id() -> str:
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        raise RuntimeError("Missing GOOGLE_SHEET_ID environment variable.")
    return sheet_id


def quote_sheet_name(name: str) -> str:
    return "'" + name.replace("'", "''") + "'"


def first_sheet_title(service, spreadsheet_id: str) -> str:
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise RuntimeError("Google Sheet has no tabs.")
    return sheets[0]["properties"]["title"]


def read_sheet_values(service, spreadsheet_id: str, tab_name: str) -> list[list[str]]:
    range_name = quote_sheet_name(tab_name)
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name,
    ).execute()
    return result.get("values", [])


def column_letter(count: int) -> str:
    letters = ""
    while count:
        count, remainder = divmod(count - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def parse_google_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sheet_modified_time() -> datetime | None:
    if not os.environ.get("GOOGLE_SHEET_ID") or not has_google_auth_config():
        return None
    service = drive_service()
    metadata = service.files().get(
        fileId=get_google_sheet_id(),
        fields="modifiedTime",
        supportsAllDrives=True,
    ).execute()
    modified = metadata.get("modifiedTime")
    return parse_google_time(modified) if modified else None


def run_git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def generated_content_files() -> list[str]:
    try:
        files = run_git(["ls-files"]).splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return sorted(path for path in files if any(pattern.match(path) for pattern in GENERATED_CONTENT_PATTERNS))


def latest_commit_for_path(path: str) -> tuple[str, datetime, str, str] | None:
    try:
        raw = run_git(["log", "-1", "--format=%H%x09%cI%x09%an%x09%s", "--", path])
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    if not raw or raw.count("\t") < 3:
        return None
    sha, committed_at, author, subject = raw.split("\t", 3)
    return sha, parse_google_time(committed_at), author, subject


def is_automated_sheet_sync_commit(author: str, subject: str) -> bool:
    return author == "github-actions[bot]" and subject.startswith("Sync website content from Google Sheet")


def generated_files_newer_than_sheet(sheet_time: datetime | None) -> dict[str, tuple[str, datetime]]:
    if sheet_time is None:
        return {}
    newer: dict[str, tuple[str, datetime]] = {}
    for path in generated_content_files():
        latest = latest_commit_for_path(path)
        if latest and latest[1] > sheet_time and not is_automated_sheet_sync_commit(latest[2], latest[3]):
            newer[path] = (latest[0], latest[1])
    return newer


def section_page_from_path(path: str) -> str:
    parts = Path(path).parts
    if not parts:
        return ""
    if parts[0] in {"en", "zh"}:
        language = "English" if parts[0] == "en" else "Chinese"
        if len(parts) == 2:
            return f"{language} home"
        return f"{language} / {'/'.join(parts[1:-1])}"
    if path in {"content/website-content.csv", "content/service-images.csv"}:
        return "Content source CSV"
    if path == "index.html":
        return "Language landing page"
    if path == "assets/contact.js":
        return "Contact form behavior/content"
    return ""


def trim_cell(value: str, limit: int = 4500) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 20].rstrip() + "\n...[truncated]"


def changed_text_for_file(sha: str, path: str) -> tuple[str, str]:
    try:
        diff = run_git(["diff", "--unified=0", f"{sha}^", sha, "--", path])
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "", ""

    old_lines = []
    new_lines = []
    for line in diff.splitlines():
        if not line or line.startswith(("---", "+++", "@@")):
            continue
        if line.startswith("-"):
            old_lines.append(line[1:].strip())
        elif line.startswith("+"):
            new_lines.append(line[1:].strip())
    return trim_cell("\n".join(old_lines)), trim_cell("\n".join(new_lines))


def ensure_tab_and_headers(service, spreadsheet_id: str, tab_name: str, headers: list[str]) -> None:
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    tab = next(
        (sheet for sheet in spreadsheet.get("sheets", []) if sheet.get("properties", {}).get("title") == tab_name),
        None,
    )
    if tab is None:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
        ).execute()

    last_column = column_letter(len(headers))
    header_range = f"{quote_sheet_name(tab_name)}!A1:{last_column}1"
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=header_range).execute()
    values = result.get("values", [])
    if not values or values[0] != headers:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=header_range,
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()


def append_codex_change_log(service, spreadsheet_id: str, rows: list[list[str]]) -> None:
    if not rows:
        return
    tab_name = os.environ.get("CODEX_CHANGE_LOG_TAB_NAME", CODEX_CHANGE_LOG_TAB_NAME).strip() or CODEX_CHANGE_LOG_TAB_NAME
    ensure_tab_and_headers(service, spreadsheet_id, tab_name, CODEX_CHANGE_LOG_HEADERS)
    last_column = column_letter(len(CODEX_CHANGE_LOG_HEADERS))
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{quote_sheet_name(tab_name)}!A:{last_column}",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()


def csv_rows_by_key(csv_text: str) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for raw in csv.reader(csv_text.splitlines()):
        if len(raw) < 4:
            continue
        key = raw[3].strip()
        if not key or key in {"Key", "Content Key"}:
            continue
        rows[key] = raw
    return rows


def current_csv_rows_by_key() -> dict[str, list[str]]:
    if not CONTENT.exists():
        return {}
    return csv_rows_by_key(CONTENT.read_text(encoding="utf-8-sig"))


def parent_csv_rows_by_key(sha: str) -> dict[str, list[str]]:
    try:
        old_csv = run_git(["show", f"{sha}^:content/website-content.csv"])
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}
    return csv_rows_by_key(old_csv)


def row_key_index(values: list[list[str]]) -> dict[str, list[int]]:
    matches: dict[str, list[int]] = {}
    for index, row in enumerate(values, start=1):
        if len(row) < 4:
            continue
        key = row[3].strip()
        if not key or key in {"Key", "Content Key"}:
            continue
        matches.setdefault(key, []).append(index)
    return matches


def write_clear_csv_changes_back_to_sheet(
    service,
    spreadsheet_id: str,
    tab_name: str,
    sheet_values: list[list[str]],
    csv_sha: str,
) -> tuple[bool, list[list[str]]]:
    previous = parent_csv_rows_by_key(csv_sha)
    current = current_csv_rows_by_key()
    changed_keys = sorted(key for key, row in current.items() if previous.get(key) != row)
    if not changed_keys:
        return True, []

    key_index = row_key_index(sheet_values)
    unclear_rows: list[list[str]] = []
    for key in changed_keys:
        sheet_rows = key_index.get(key, [])
        if len(sheet_rows) != 1:
            old_value = "\n".join(previous.get(key, []))
            new_value = "\n".join(current.get(key, []))
            unclear_rows.append(
                [
                    now_iso(),
                    "content/website-content.csv",
                    "Content source CSV",
                    trim_cell(old_value),
                    trim_cell(new_value),
                    csv_sha,
                    "Codex",
                    f"Review manually: content key '{key}' does not match exactly one Google Sheet row.",
                ]
            )
            continue

        row_number = sheet_rows[0]
        row = current[key]
        last_column = column_letter(len(row))
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{quote_sheet_name(tab_name)}!A{row_number}:{last_column}{row_number}",
            valueInputOption="RAW",
            body={"values": [row]},
        ).execute()

    return not unclear_rows, unclear_rows


def protect_newer_codex_changes() -> None:
    sheet_time = sheet_modified_time()
    newer = generated_files_newer_than_sheet(sheet_time)
    if not newer:
        return

    service = sheets_service()
    spreadsheet_id = get_google_sheet_id()
    tab_name = os.environ.get("GOOGLE_SHEET_TAB_NAME", DEFAULT_SHEET_TAB_NAME).strip() or DEFAULT_SHEET_TAB_NAME
    try:
        sheet_values = read_sheet_values(service, spreadsheet_id, tab_name)
    except Exception:  # noqa: BLE001
        if os.environ.get("GOOGLE_SHEET_TAB_NAME"):
            raise
        tab_name = first_sheet_title(service, spreadsheet_id)
        sheet_values = read_sheet_values(service, spreadsheet_id, tab_name)

    log_rows: list[list[str]] = []
    csv_latest = newer.pop("content/website-content.csv", None)
    if csv_latest:
        synced, unclear_rows = write_clear_csv_changes_back_to_sheet(
            service,
            spreadsheet_id,
            tab_name,
            sheet_values,
            csv_latest[0],
        )
        log_rows.extend(unclear_rows)
        if not synced:
            newer["content/website-content.csv"] = csv_latest

    for path, (sha, _committed_at) in newer.items():
        old_value, new_value = changed_text_for_file(sha, path)
        log_rows.append(
            [
                now_iso(),
                path,
                section_page_from_path(path),
                old_value,
                new_value,
                sha,
                "Codex",
                "Review manually: matching Google Sheet row is unclear, so the sync did not overwrite either side.",
            ]
        )

    if log_rows:
        append_codex_change_log(service, spreadsheet_id, log_rows)
        raise RuntimeError(
            "Stopped Google Sheet sync because newer direct website content changes need review in Codex Change Log."
        )

    print("Newer direct CSV content changes were written back to the Google Sheet before sync.")


def export_google_sheet_to_csv() -> None:
    if not os.environ.get("GOOGLE_SHEET_ID") and not has_google_auth_config():
        return
    if not os.environ.get("GOOGLE_SHEET_ID"):
        raise RuntimeError("GOOGLE_SHEET_ID is required when Google authentication is configured.")
    if not has_google_auth_config():
        raise RuntimeError(
            "Google authentication is not configured. Use GitHub OIDC via GOOGLE_WORKLOAD_IDENTITY_PROVIDER "
            "or set GOOGLE_SERVICE_ACCOUNT_JSON to the full service-account JSON."
        )

    service = sheets_service()
    spreadsheet_id = get_google_sheet_id()
    tab_name = os.environ.get("GOOGLE_SHEET_TAB_NAME", DEFAULT_SHEET_TAB_NAME).strip() or DEFAULT_SHEET_TAB_NAME

    try:
        values = read_sheet_values(service, spreadsheet_id, tab_name)
    except Exception:  # noqa: BLE001
        if os.environ.get("GOOGLE_SHEET_TAB_NAME"):
            raise
        tab_name = first_sheet_title(service, spreadsheet_id)
        values = read_sheet_values(service, spreadsheet_id, tab_name)

    if not values:
        raise RuntimeError(f"Google Sheet tab '{tab_name}' is empty.")

    max_columns = max(len(row) for row in values)
    CONTENT.parent.mkdir(parents=True, exist_ok=True)
    with CONTENT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in values:
            writer.writerow(row + [""] * (max_columns - len(row)))
    print(f"Exported Google Sheet tab '{tab_name}' to {CONTENT.relative_to(ROOT)}.")

    image_tab_name = os.environ.get("GOOGLE_SERVICE_IMAGES_TAB_NAME", SERVICE_IMAGES_TAB_NAME).strip() or SERVICE_IMAGES_TAB_NAME
    try:
        image_values = read_sheet_values(service, spreadsheet_id, image_tab_name)
    except Exception as exc:  # noqa: BLE001
        print(f"Skipped service image export because tab '{image_tab_name}' was not readable: {exc}")
        return

    service_image_rows = normalize_service_image_values(image_values)
    if not service_image_rows:
        raise RuntimeError(f"Google Sheet tab '{image_tab_name}' did not contain usable service image rows.")
    write_service_images_csv(service_image_rows)
    print(f"Exported Google Sheet tab '{image_tab_name}' to {SERVICE_IMAGES.relative_to(ROOT)}.")


def verify_google_drive_folder_access() -> None:
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        return
    if not has_google_auth_config():
        raise RuntimeError(
            "GOOGLE_DRIVE_FOLDER_ID requires Google authentication through OIDC or GOOGLE_SERVICE_ACCOUNT_JSON."
        )

    service = drive_service()
    folder = service.files().get(
        fileId=folder_id,
        fields="id,name,mimeType",
        supportsAllDrives=True,
    ).execute()
    if folder.get("mimeType") != "application/vnd.google-apps.folder":
        raise RuntimeError(f"GOOGLE_DRIVE_FOLDER_ID is not a Google Drive folder: {folder_id}")

    result = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id,name,mimeType,modifiedTime)",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        pageSize=100,
        orderBy="name",
    ).execute()
    files = result.get("files", [])
    print(f"Verified Google Drive folder '{folder.get('name')}' with {len(files)} visible item(s).")


def text(key: str, lang: str, fallback: str = "") -> str:
    row = ROWS.get(key, {})
    return row.get(lang, "") or fallback


def service_href(lang: str, section_id: str, link: str = "") -> str:
    if link:
        target = link.strip()
        if target.startswith("http://") or target.startswith("https://") or target.startswith("/"):
            return target
        if "#" in target:
            anchor = target.split("#", 1)[1]
            return f"/{lang}/services/#{anchor}"
    return f"/{lang}/services/#{section_id}"


def home_core_services(lang: str) -> list[dict[str, str]]:
    is_en = lang == "en"
    allowlist = [
        ("elite-private-school", "service_prep_title", "School Admissions", "學校申請"),
        ("university-application", "service_university_title", "University Applications", "大學申請"),
        ("strategic-planning", "service_education_strategy_title", "Academic Strategy", "學術策略"),
        ("steam-pathway", "steam_title", "STEAM Development", "STEAM 發展"),
        ("student-athlete", "athlete_title", "Student-Athlete Planning", "學生運動員規劃"),
        (
            "gifted-diverse-learning",
            "gifted_title",
            "Gifted, High-Potential & Neurodiverse Learner Support",
            "高智商、高潛能與多元神經譜系學生支持",
        ),
    ]
    services: list[dict[str, str]] = []
    for section_id, key, *home_label in allowlist:
        row = ROWS.get(key, {})
        if row.get("status") and row.get("status") != "Approved":
            continue
        label = home_label[0 if is_en else 1] if home_label else text(key, lang)
        if not label:
            continue
        href = service_href(lang, row.get("section_id") or section_id, row.get("link", ""))
        services.append({"title": label, "href": href})
    return services


def replace_between(source: str, start_pattern: str, end_pattern: str, replacement: str) -> str:
    pattern = re.compile(start_pattern + r".*?" + end_pattern, re.S)
    if not pattern.search(source):
        raise RuntimeError(f"Could not find block: {start_pattern} ... {end_pattern}")
    return pattern.sub(replacement, source, count=1)


def update_common_headers() -> None:
    en_tagline = text("footer_tagline", "en", "Strategic education consulting for future-ready students.")
    zh_tagline = text("footer_tagline", "zh", "面向未來學生的戰略教育諮詢")
    html_files = list((ROOT / "en").glob("**/*.html")) + list((ROOT / "zh").glob("**/*.html"))
    for path in html_files:
        source = path.read_text(encoding="utf-8")
        lang = "en" if path.relative_to(ROOT).parts[0] == "en" else "zh"
        tagline = en_tagline if lang == "en" else zh_tagline
        source = re.sub(r"<small>.*?</small></a>", f"<small>{esc(tagline)}</small></a>", source, count=1)
        path.write_text(source, encoding="utf-8")


def hero_section(lang: str) -> str:
    is_en = lang == "en"
    hero_img = "/assets/images/animetro-hero-banner-0617.png"
    alt = "Animetro education consultation with a family and students" if is_en else "艾美加教育顧問家庭教育諮詢場景"
    eyebrow = "Parent-friendly planning for future-ready students" if is_en else "艾美加教育顧問"
    primary_link = "/en/contact/" if is_en else "contact/"
    secondary_link = "/en/services/" if is_en else "services/"
    core_title = "Core Services" if is_en else "核心服務"
    primary_label = "Book a Free Consultation" if is_en else "預約免費諮詢"
    items = []
    for service in home_core_services(lang):
        items.append(
            f"""            <li>
              <a href="{esc(service["href"])}">
                <span>{esc(service["title"])}</span>
              </a>
            </li>"""
        )

    return f"""      <section class="hero">
        <div>
          <figure class="hero-media">
            <img src="{hero_img}" alt="{esc(alt)}">
          </figure>
          <p class="eyebrow">{esc(eyebrow)}</p>
          <h1>{esc(text("hero_title", lang))}</h1>
          <p class="lead">{esc(text("hero_subtitle", lang))}</p>
          <div class="actions">
            <a class="button" href="{primary_link}">{esc(primary_label)}</a>
            <a class="button secondary" href="{secondary_link}">{esc(text("hero_secondary_cta", lang))}</a>
          </div>
        </div>
        <aside class="hero-card" aria-label="{esc(core_title)}">
          <h2>{esc(core_title)}</h2>
          <ul>
{chr(10).join(items)}
          </ul>
        </aside>
      </section>"""


def why_process_testimonials_contact(lang: str) -> str:
    is_en = lang == "en"
    family = "Family Trust" if is_en else "家庭信任"
    process_eye = "Process" if is_en else "流程"
    testimonial_eye = "Testimonials" if is_en else "反饋"
    contact_href = "/en/contact/" if is_en else "contact/"
    services_href = "/en/services/" if is_en else "services/"
    services_label = "Explore Our Services" if is_en else "了解我們的服務"
    contact_label = "Book a Free Consultation" if is_en else "預約免費諮詢"

    why_cards = "\n".join(
        f"""            <article class="why-card">
              <h3>{esc(text(f"why_{i}", lang))}</h3>
            </article>"""
        for i in range(1, 5)
        if text(f"why_{i}", lang)
    )

    process_cards = []
    for i in range(1, 5):
        process_cards.append(
            f"""            <article class="process-card">
              <span class="process-number">{i:02d}</span>
              <h3>{esc(text(f"process_step_{i}_title", lang, text(f"process_{i}", lang)))}</h3>
              <p>{esc(text(f"process_step_{i}_desc", lang))}</p>
            </article>"""
        )

    testimonial_items: list[tuple[str, str]] = []
    grade11 = text("testimonial_grade11_parent", lang)
    if grade11:
        testimonial_items.append((grade11, "Grade 11 Parent" if is_en else "十一年級學生家長"))
    for quote_key, author_key in [
        ("testimonial_three_children_growth_quote", "testimonial_three_children_growth_author"),
        ("testimonial_neurodiversity_growth_quote", "testimonial_neurodiversity_growth_author"),
    ]:
        quote = text(quote_key, lang)
        if quote:
            testimonial_items.append((quote, text(author_key, lang)))
    for i in range(1, 4):
        quote = text(f"testimonial_{i}", lang)
        if quote:
            testimonial_items.append((quote, text(f"testimonial_{i}_author", lang)))

    testimonials = [
        f"""            <article class="testimonial-card">
              <p>{keep_breaks(quote)}</p>
              <span>{esc(author)}</span>
            </article>"""
        for quote, author in testimonial_items
    ]

    return f"""      <section class="why-section">
        <div class="section">
          <div class="why-header">
            <p class="eyebrow">{esc(family)}</p>
            <h2>{esc(text("why_title", lang))}</h2>
          </div>
          <div class="why-grid">
{why_cards}
          </div>
        </div>
      </section>

      <section class="process-section">
        <div class="section">
          <div class="section-header process-header">
            <div>
              <p class="eyebrow">{esc(process_eye)}</p>
              <h2>{esc(text("process_title", lang))}</h2>
            </div>
            <p>{esc(text("process_subtitle", lang))}</p>
          </div>
          <div class="process-grid" aria-label="{esc(text("process_title", lang))}">
{chr(10).join(process_cards)}
          </div>
        </div>
      </section>

      <section class="testimonials-section">
        <div class="section">
          <div class="section-header testimonials-header">
            <div>
              <p class="eyebrow">{esc(testimonial_eye)}</p>
              <h2>{esc(text("testimonials_title", lang))}</h2>
            </div>
            <p>{esc(text("testimonials_subtitle", lang))}</p>
          </div>
          <div class="testimonial-grid" aria-label="{esc(text("testimonials_title", lang))}">
{chr(10).join(testimonials)}
          </div>
        </div>
      </section>

      <section class="band">
        <div class="section">
          <div class="section-header">
            <h2>{esc(text("contact_cta_title", lang))}</h2>
          </div>
          <div class="actions">
            <a class="button" href="{contact_href}">{esc(contact_label)}</a>
            <a class="button secondary" href="{services_href}">{esc(services_label)}</a>
          </div>
        </div>
      </section>"""


def update_homepage(lang: str) -> None:
    path = ROOT / lang / "index.html"
    source = path.read_text(encoding="utf-8")
    source = replace_between(source, r"      <section class=\"hero\">", r"      </section>\n\n      <section class=\"philosophy-section\">", hero_section(lang) + "\n\n      <section class=\"philosophy-section\">")
    source = replace_between(source, r"      <section class=\"why-section\">", r"      </section>\n    </main>", why_process_testimonials_contact(lang) + "\n    </main>")
    path.write_text(source, encoding="utf-8")


def service_text(value: object, lang: str) -> str:
    if isinstance(value, dict):
        text_value = value.get(lang) or value.get("en") or ""
        return str(text_value)
    return ""


def service_points(value: object, lang: str) -> list[str]:
    if isinstance(value, dict):
        points = value.get(lang) or value.get("en") or []
        if isinstance(points, list):
            return [str(point) for point in points if str(point)]
    return []


def service_image_figure(service: dict[str, object], lang: str) -> str:
    service_id = str(service.get("service_id", ""))
    image = service.get("image", {})
    if not isinstance(image, dict):
        image = {}
    image_url = str(image.get("image_url") or SERVICE_PLACEHOLDER_IMAGE)
    image_file_name = str(image.get("image_file_name") or Path(image_url).name or "service-image-pending.svg")
    image_alt = (
        SERVICE_IMAGE_ALT.get(service_id, {}).get(lang)
        or str(image.get("image_alt") or "")
        or service_text(service.get("title"), lang)
        or "Service image pending"
    )
    image_purpose = str(image.get("image_purpose") or f"Service page visual for {service_id}")
    image_status = str(image.get("image_status") or "In Progress")
    drive_link = str(image.get("drive_link") or "")
    live_image_rule = str(image.get("live_image_rule") or "Do not replace existing live image")
    recommended_action = str(image.get("recommended_action") or "")
    is_placeholder = str(image.get("is_placeholder") or ("true" if image_url == SERVICE_PLACEHOLDER_IMAGE else "false"))

    return f"""            <figure class="service-image" data-image-file-name="{esc(image_file_name)}" data-image-url="{esc(image_url)}" data-image-alt="{esc(image_alt)}" data-image-purpose="{esc(image_purpose)}" data-image-status="{esc(image_status)}" data-drive-link="{esc(drive_link)}" data-live-image-rule="{esc(live_image_rule)}" data-recommended-action="{esc(recommended_action)}" data-placeholder="{esc(is_placeholder)}">
              <img src="{esc(image_url)}" alt="{esc(image_alt)}">
            </figure>"""


def service_article(service: dict[str, object], lang: str) -> str:
    service_id = str(service.get("service_id", ""))
    title = service_text(service.get("title"), lang)
    subtitle = service_text(service.get("subtitle"), lang)
    description = service_text(service.get("description"), lang)
    points = service_points(service.get("points"), lang)
    intro = " ".join(part for part in [subtitle, description] if part)
    bullet_list = "\n".join(f"              <li>{esc(point)}</li>" for point in points)

    subsections = []
    for subsection in service.get("subsections", []):
        if not isinstance(subsection, dict):
            continue
        subsection_title = service_text(subsection.get("title"), lang)
        subsection_description = service_text(subsection.get("description"), lang)
        subsection_points = service_points(subsection.get("points"), lang)
        if not subsection_title and not subsection_description and not subsection_points:
            continue
        subsection_bullets = "\n".join(f"              <li>{esc(point)}</li>" for point in subsection_points)
        subsections.append(
            f"""            <h3>{esc(subsection_title)}</h3>
            <p>{esc(subsection_description)}</p>
            <ul>
{subsection_bullets}
            </ul>"""
        )

    return f"""          <article class="service-detail" id="{esc(service_id)}" data-service-id="{esc(service_id)}">
            <h2>{esc(title)}</h2>
{service_image_figure(service, lang)}
            <p>{esc(intro)}</p>
            <ul>
{bullet_list}
            </ul>
{chr(10).join(subsections)}
          </article>"""


def services_main(lang: str) -> str:
    is_en = lang == "en"
    eyebrow = "Services" if is_en else "服務"
    title = "Education planning with a clear strategy." if is_en else "完整服務系統"
    lead = (
        "Services include school admissions, university applications, academic strategy, STEAM development, student-athlete planning, and support for gifted, high-potential, and neurodiverse learners."
        if is_en
        else "服務涵蓋學校申請、大學申請、學術策略、STEAM 發展、學生運動員規劃，以及高智商、高潛能與多元神經譜系學生支持。"
    )
    services = "\n".join(service_article(service, lang) for service in load_services_data())
    return f"""    <main>
      <section class="page-hero">
        <p class="eyebrow">{esc(eyebrow)}</p>
        <h1>{esc(title)}</h1>
        <p class="lead">{esc(lead)}</p>
      </section>

      <section class="section">
        <div class="service-list" data-content-source="content/services.json">
{services}
        </div>
      </section>
    </main>"""


def update_services_page(lang: str) -> None:
    path = ROOT / lang / "services" / "index.html"
    source = path.read_text(encoding="utf-8")
    source = replace_between(source, r"    <main>", r"    </main>", services_main(lang))
    path.write_text(source, encoding="utf-8")


def keep_breaks(value: str) -> str:
    return "<br>\n".join(esc(line.strip()) for line in value.splitlines() if line.strip())


def parse_profile(value: str) -> tuple[str, str, list[str], list[str]]:
    value = (value or "").strip()
    if not value:
        return "", "", [], []

    if "|" in value or "｜" in value:
        name, remainder = re.split(r"\s*[|｜]\s*", value, maxsplit=1)
    else:
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        return (lines[0] if lines else "", lines[1] if len(lines) > 1 else "", [], lines[2:])

    remainder = remainder.strip()
    if "\n\n" in remainder:
        blocks = [block.strip() for block in re.split(r"\n\s*\n", remainder) if block.strip()]
        role = blocks[0] if blocks else ""
        credentials = blocks[1:3]
        body = blocks[3:]
        return name.strip(), role.strip(), credentials, body

    parts = [p.strip() for p in re.split(r"\s*[|｜]\s*", value) if p.strip()]
    name = parts[0] if parts else ""
    role = parts[1] if len(parts) > 1 else ""
    rest = parts[2:]
    if len(rest) <= 1:
        return name, role, [], rest
    return name, role, rest[:-1], rest[-1:]


def team_card(key: str, lang: str, image: str) -> str:
    value = text(key, lang)
    name, role, credentials, body = parse_profile(value)
    paragraphs = [f"            <p class=\"team-credential\">{keep_breaks(part)}</p>" for part in credentials]
    paragraphs.extend(f"            <p>{keep_breaks(part)}</p>" for part in body)
    return f"""          <article class="team-card">
            <figure class="team-portrait">
              <img src="/assets/images/team/{image}" alt="{esc(name)}">
            </figure>
            <h3>{esc(name)}</h3>
            <p class="team-role">{esc(role)}</p>
{chr(10).join(paragraphs)}
          </article>"""


def update_team(lang: str) -> None:
    path = ROOT / lang / "about" / "index.html"
    source = path.read_text(encoding="utf-8")
    title = text("team_title", lang)
    intro = text("team_intro", lang)
    cards = [
        team_card("team_emily", lang, "emily-founder-portrait.png"),
        team_card("team_Leonard", lang, "dr-leonard-li-advisor-portrait.png"),
        team_card("team_frances", lang, "frances-team-portrait.png"),
        team_card("team_lloyd", lang, "lloyd-advisor-portrait.png"),
        team_card("team_David", lang, "dr-wong-advisor-portrait.png"),
        team_card("team_brooke", lang, "brooke-art-director-portrait.png"),
    ]
    block = f"""      <section class="section team-section">
        <div class="section-header">
          <h2>{esc(title)}</h2>
          <p>{esc(intro)}</p>
        </div>
        <div class="team-grid">
{chr(10).join(cards)}
        </div>
      </section>"""
    source = replace_between(source, r"      <section class=\"section team-section\">", r"      </section>\n\n      <section class=\"band\">", block + "\n\n      <section class=\"band\">")
    path.write_text(source, encoding="utf-8")


def update_about_process(lang: str) -> None:
    path = ROOT / lang / "about" / "index.html"
    source = path.read_text(encoding="utf-8")
    heading = "Our Process" if lang == "en" else "我們的諮詢流程"
    cards = []
    for i in range(1, 5):
        cards.append(
            f"""                <li>
                  <strong>{esc(text(f"process_step_{i}_title", lang, text(f"process_{i}", lang)))}</strong>
                  <span>{esc(text(f"process_step_{i}_desc", lang))}</span>
                </li>"""
        )
    block = f"""          <article class="contact-panel">
            <h2>{esc(heading)}</h2>
            <ol class="about-process-list">
{chr(10).join(cards)}
            </ol>
          </article>"""
    pattern = re.compile(r"          <article class=\"contact-panel\">\s*<h2>(?:Our Process|我們的諮詢流程)</h2>.*?          </article>", re.S)
    if not pattern.search(source):
        raise RuntimeError(f"Could not find About process panel for {lang}")
    source = pattern.sub(block, source, count=1)
    path.write_text(source, encoding="utf-8")


def update_contact(lang: str) -> None:
    path = ROOT / lang / "contact" / "index.html"
    source = path.read_text(encoding="utf-8")
    def field_value(key: str) -> str:
        value = text(key, lang)
        return re.split(r"[:：]", value, maxsplit=1)[-1].strip()

    phone = field_value("contact_phone")
    email = field_value("contact_email")
    address = field_value("contact_address")
    labels = ("Phone", "Email", "Address") if lang == "en" else ("電話", "電郵", "地址")
    details = f"""          <div class="contact-details" aria-label="Animetro contact details">
            <p><span>{labels[0]}</span><a href="tel:+19059557068">{esc(phone)}</a></p>
            <p><span>{labels[1]}</span><a href="mailto:{esc(email)}">{esc(email)}</a></p>
            <p><span>{labels[2]}</span><span>{esc(address)}</span></p>
          </div>"""
    source = re.sub(r"          <div class=\"contact-details\".*?</div>", details, source, count=1, flags=re.S)
    path.write_text(source, encoding="utf-8")


def sync_dist() -> None:
    dist = ROOT / "dist"
    if not dist.exists():
        return
    for name in ["index.html", "vercel.json"]:
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, dist / name)
    for folder in ["en", "zh", "assets", "content"]:
        src = ROOT / folder
        dst = dist / folder
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def main() -> None:
    global ROWS, SERVICE_IMAGE_ROWS

    protect_newer_codex_changes()
    export_google_sheet_to_csv()
    verify_google_drive_folder_access()
    ROWS = load_rows()
    SERVICE_IMAGE_ROWS = load_service_images()
    write_services_json()
    update_common_headers()
    update_homepage("en")
    update_homepage("zh")
    update_services_page("en")
    update_services_page("zh")
    update_about_process("en")
    update_about_process("zh")
    update_team("en")
    update_team("zh")
    update_contact("en")
    update_contact("zh")
    sync_dist()


if __name__ == "__main__":
    main()
