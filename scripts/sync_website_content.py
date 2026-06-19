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
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]
DEFAULT_SHEET_TAB_NAME = "Website Copy"
CODEX_CHANGE_LOG_TAB_NAME = "Codex Change Log"
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
    re.compile(r"^content/website-content\.csv$"),
    re.compile(r"^assets/contact\.js$"),
)


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


def sheets_service():
    return google_service("sheets", "v4")


def drive_service():
    return google_service("drive", "v3")


def google_service(api_name: str, api_version: str):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

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
    if not os.environ.get("GOOGLE_SHEET_ID") or not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
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
    if path == "content/website-content.csv":
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
    if not os.environ.get("GOOGLE_SHEET_ID") and not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        return

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


def verify_google_drive_folder_access() -> None:
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        return
    if not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID requires GOOGLE_SERVICE_ACCOUNT_JSON.")

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
        ("strategic-planning", "service_education_strategy_title", "Education Strategy", "教育规划与整体战略"),
        ("elite-private-school", "service_prep_title", "Prep School Admissions", "贵族私校申请"),
        ("school-visit-interview", "school_visit_title", "School Visit & Interview Preparation", "学校参观与面试准备"),
        ("university-application", "service_university_title", "University Admissions", "大学申请"),
        ("gpa-management", "service_gpa_title", "GPA Management", "GPA 管理"),
        ("steam-pathway", "steam_title", "STEAM Pathway", "STEM/STEAM 规划"),
        ("student-athlete", "athlete_title", "Student-Athlete Planning", "学生运动员规划"),
        ("gifted-diverse-learning", "gifted_title", "Gifted & Neurodiversity Support", "资优与神经多样化支持"),
        ("mental-health-support", "mental_health_title", "Student Mental Health Support", "学生心理健康支持"),
        ("short-term-guardianship", "guardianship_title", "Short-Term Guardianship", "短期监护/寄宿监护"),
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
    hero_img = "/assets/images/hero-consulting-1.jpg" if is_en else "/assets/images/hero-consulting-2.jpg"
    alt = "Animetro education consultation with a family and students" if is_en else "艾美加教育顧問家庭教育諮詢場景"
    eyebrow = "Parent-friendly planning for future-ready students" if is_en else "艾美加教育顧問"
    primary_link = "/en/contact/" if is_en else "contact/"
    secondary_link = "/en/services/" if is_en else "services/"
    core_title = "Core Services" if is_en else "核心服務"
    primary_label = "Book a Free Private Consultation" if is_en else "預約一次免費諮詢"
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
    services_label = "Explore Services" if is_en else "查看完整服務"
    contact_label = "Book a Free Private Consultation" if is_en else "預約一次免費諮詢"

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
    global ROWS

    protect_newer_codex_changes()
    export_google_sheet_to_csv()
    verify_google_drive_folder_access()
    ROWS = load_rows()
    update_common_headers()
    update_homepage("en")
    update_homepage("zh")
    update_about_process("en")
    update_about_process("zh")
    update_team("en")
    update_team("zh")
    update_contact("en")
    update_contact("zh")
    sync_dist()


if __name__ == "__main__":
    main()
