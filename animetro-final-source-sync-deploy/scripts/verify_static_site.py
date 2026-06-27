#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_HERO = {
    "en": {
        "h1": "Growth Beyond Admissions",
        "lead": "Personalized education pathway planning for students and families — from school admissions and university applications to academic strategy, STEAM development, student-athlete planning, and support for gifted, high-potential, and neurodiverse learners.",
    },
    "zh": {
        "h1": "成長超越升學",
        "lead": "為學生與家庭提供個性化教育路徑規劃，涵蓋學校申請、大學申請、學術策略、STEAM 發展、學生運動員規劃，以及高智商、高潛能與多元神經譜系學生支持。",
    },
}

REQUIRED_IMAGE_FIELDS = {
    "image_url",
    "image_alt",
    "image_purpose",
    "image_status",
    "image_file_name",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.h1_texts: list[str] = []
        self.leads: list[str] = []
        self.figures: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.service_source_found = False
        self.service_article_ids: list[str] = []
        self._capture: str | None = None
        self._capture_end_tag: str | None = None
        self._buffer: list[str] = []
        self._current_figure: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        self.stack.append(tag)
        if tag == "h1":
            self._capture = "h1"
            self._capture_end_tag = "h1"
            self._buffer = []
        elif tag == "p" and "lead" in attr.get("class", "").split():
            self._capture = "lead"
            self._capture_end_tag = "p"
            self._buffer = []
        elif tag == "figure" and "service-image" in attr.get("class", "").split():
            self._current_figure = attr
        elif tag == "div" and "service-list" in attr.get("class", "").split():
            if attr.get("data-content-source") == "content/services.json":
                self.service_source_found = True
        elif tag == "article" and "service-detail" in attr.get("class", "").split():
            service_id = attr.get("data-service-id") or attr.get("id")
            if service_id:
                self.service_article_ids.append(service_id)
        elif tag == "img":
            self.images.append(attr)
            if self._current_figure is not None:
                self._current_figure["img_src"] = attr.get("src", "")
                self._current_figure["img_alt"] = attr.get("alt", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "figure" and self._current_figure is not None:
            self.figures.append(self._current_figure)
            self._current_figure = None
        if self._capture and self._capture_end_tag == tag:
            text = re.sub(r"\s+", " ", "".join(self._buffer)).strip()
            if self._capture == "h1":
                self.h1_texts.append(text)
            elif self._capture == "lead":
                self.leads.append(text)
            self._capture = None
            self._capture_end_tag = None
            self._buffer = []
        if self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def verify_homepage(lang: str) -> None:
    parser = parse_page(ROOT / lang / "index.html")
    expected = EXPECTED_HERO[lang]
    if not parser.h1_texts or parser.h1_texts[0] != expected["h1"]:
        fail(f"{lang} homepage hero h1 mismatch: {parser.h1_texts[:1]}")
    if not parser.leads or parser.leads[0] != expected["lead"]:
        fail(f"{lang} homepage hero lead mismatch: {parser.leads[:1]}")


def verify_service_images_csv() -> dict[str, dict[str, str]]:
    path = ROOT / "content" / "service-images.csv"
    if not path.exists():
        fail("content/service-images.csv is missing")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_IMAGE_FIELDS - set(reader.fieldnames or [])
        if missing:
            fail(f"content/service-images.csv missing required fields: {sorted(missing)}")
        rows = {row["service_id"]: row for row in reader if row.get("service_id")}
    if not rows:
        fail("content/service-images.csv has no service rows")
    for service_id, row in rows.items():
        for field in REQUIRED_IMAGE_FIELDS:
            if not row.get(field):
                fail(f"{service_id} missing {field}")
        if row.get("image_status") == "Implemented":
            fail(f"{service_id} image_status must not be Implemented while Service Images is in progress")
    return rows


def verify_services_json(image_rows: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    path = ROOT / "content" / "services.json"
    if not path.exists():
        fail("content/services.json is missing")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("status") == "Implemented":
        fail("content/services.json must not mark Service Images as Implemented")
    services = data.get("services")
    if not isinstance(services, list) or not services:
        fail("content/services.json has no services")
    for service in services:
        if not isinstance(service, dict):
            fail("content/services.json contains a non-object service")
        service_id = service.get("service_id")
        if not service_id:
            fail("content/services.json service missing service_id")
        for field in ("title", "description", "points"):
            if field not in service:
                fail(f"{service_id} missing service field: {field}")
        image = service.get("image")
        if not isinstance(image, dict):
            fail(f"{service_id} missing structured image object")
        for field in REQUIRED_IMAGE_FIELDS:
            if not image.get(field):
                fail(f"{service_id} services.json image missing {field}")
        if image.get("image_status") == "Implemented":
            fail(f"{service_id} services.json image_status must not be Implemented")
        csv_row = image_rows.get(str(service_id))
        if csv_row and image.get("is_placeholder") != "true":
            if image.get("image_url") != csv_row.get("image_url"):
                fail(f"{service_id} services.json image_url does not match content/service-images.csv")
            image_path = ROOT / str(image["image_url"]).lstrip("/")
            if not image_path.exists():
                fail(f"{service_id} missing local image was not converted to placeholder")
    return services


def verify_services_page(lang: str, services: list[dict[str, object]]) -> None:
    parser = parse_page(ROOT / lang / "services" / "index.html")
    if not parser.service_source_found:
        fail(f"{lang} services page is not marked as generated from content/services.json")
    service_ids = {str(service.get("service_id", "")) for service in services}
    if set(parser.service_article_ids) != service_ids:
        fail(f"{lang} services articles do not match content/services.json")
    figures = {
        figure.get("data-image-file-name", ""): figure
        for figure in parser.figures
        if figure.get("data-image-file-name")
    }
    for service in services:
        image = service.get("image")
        if not isinstance(image, dict):
            fail(f"{service.get('service_id')} missing image object")
        figure = figures.get(str(image["image_file_name"]))
        if figure is None:
            fail(f"{lang} services page does not consume image_file_name={image['image_file_name']}")
        if figure.get("data-image-url") != image["image_url"]:
            fail(f"{lang} services image_url mismatch for {service['service_id']}")
        if figure.get("img_src") != image["image_url"]:
            fail(f"{lang} services img src mismatch for {service['service_id']}")
        if not figure.get("data-image-alt") or not figure.get("img_alt"):
            fail(f"{lang} services missing alt data for {service['service_id']}")
        if not figure.get("data-image-purpose"):
            fail(f"{lang} services missing image purpose for {service['service_id']}")
        if figure.get("data-image-status") == "Implemented":
            fail(f"{lang} services image status must not be Implemented")
        if image.get("is_placeholder") == "true" and figure.get("data-placeholder") != "true":
            fail(f"{lang} services placeholder state missing for {service['service_id']}")


def main() -> None:
    image_rows = verify_service_images_csv()
    services = verify_services_json(image_rows)
    verify_homepage("en")
    verify_homepage("zh")
    verify_services_page("en", services)
    verify_services_page("zh", services)
    print("Static site verification passed.")


if __name__ == "__main__":
    main()
