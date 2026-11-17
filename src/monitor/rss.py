"""Leitura de feeds RSS 2.0, Atom e RSS 1.0 (RDF)."""
from __future__ import annotations

import email.utils
import html
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

USER_AGENT = (
    "Mozilla/5.0 (compatible; DashInvestMonitor/1.0; "
    "+https://github.com/nat-rib/dash-invest)"
)


@dataclass(frozen=True)
class FeedItem:
    title: str
    link: str
    summary: str
    published_at: datetime | None


def fetch_feed(url: str, *, timeout: float = 15.0, retries: int = 1) -> bytes:
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for attempt in range(retries + 1):
            response = client.get(url)
            if response.status_code in {429, 503} and attempt < retries:
                retry_after = response.headers.get("Retry-After", "")
                delay = float(retry_after) if retry_after.isdigit() else 5.0
                time.sleep(min(delay, 15.0))
                continue
            response.raise_for_status()
            return response.content
    raise RuntimeError("feed indisponível após tentativas")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _strip_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(without_tags).split())


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _child(element: ET.Element, name: str) -> ET.Element | None:
    for child in element:
        if _local(child.tag) == name:
            return child
    return None


def _link(element: ET.Element) -> str:
    direct = _child(element, "link")
    if direct is not None and direct.text and direct.text.strip():
        return direct.text.strip()
    for child in element:
        if _local(child.tag) == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
    # RSS 1.0 usa rdf:about no item.
    return element.attrib.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", "").strip()


def parse_feed(payload: bytes) -> list[FeedItem]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise ValueError("feed XML inválido") from error

    items: list[FeedItem] = []
    seen: set[str] = set()
    for element in root.iter():
        if _local(element.tag) not in {"item", "entry"}:
            continue
        title = _text(_child(element, "title"))
        link = _link(element)
        if not title or not link or link in seen:
            continue
        summary = _text(_child(element, "description"))
        if not summary:
            summary = _text(_child(element, "summary")) or _text(_child(element, "content"))
        published = _text(_child(element, "pubDate")) or _text(
            _child(element, "published")
        ) or _text(_child(element, "updated")) or _text(_child(element, "date"))
        seen.add(link)
        items.append(
            FeedItem(
                title=_strip_html(title)[:500],
                link=link,
                summary=_strip_html(summary)[:2000],
                published_at=_parse_date(published),
            )
        )
    return items
