#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "website-content.csv"


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
                link = raw[8] if len(raw) > 8 else ""
                image = raw[9] if len(raw) > 9 else ""
                status = raw[10] if len(raw) > 10 else ""
            else:
                page, section, key, en, zh = raw[:5]
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
                "status": status,
                "link": link,
                "image": image,
            }
    return rows


ROWS = load_rows()


def text(key: str, lang: str, fallback: str = "") -> str:
    row = ROWS.get(key, {})
    return row.get(lang, "") or fallback


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
    learn = "Learn More" if is_en else "了解更多"

    home_core_services = [
        ("strategic-planning", "Education Strategy", "全方位戰略教育規劃"),
        ("elite-private-school", "Prep School Admissions", "私校申請"),
        ("school-visit-interview", "School Visit & Interview Preparation", "訪校與面試準備"),
        ("university-application", "University Admissions", "大學申請"),
        ("gpa-management", "GPA Management", "GPA 管理"),
        ("steam-pathway", "STEAM Pathway", "STEAM 路徑"),
        ("student-athlete", "Student-Athlete Planning", "學生運動員規劃"),
        ("gifted-diverse-learning", "Gifted & Neurodiversity Support", "天賦與神經多元支持"),
        ("mental-health-support", "Student Mental Health Support", "學生心理健康支持"),
        ("short-term-guardianship", "Short-Term Guardianship", "短期監護"),
    ]
    items = []
    for anchor, en_label, zh_label in home_core_services:
        label = en_label if is_en else zh_label
        href = f"/{lang}/services/#{anchor}"
        items.append(
            f"""            <li>
              <a href="{href}">
                <span>{esc(label)}</span>
                <span class="learn-more">{learn}</span>
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
            <a class="button" href="{primary_link}">{esc(text("hero_primary_cta", lang))}</a>
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
            <a class="button" href="{contact_href}">{esc(text("contact_cta_button", lang))}</a>
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
