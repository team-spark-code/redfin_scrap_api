# backend/utils/opml_parser.py
from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Set
from backend.utils.url_norm import normalize_url, sanitize_opml_bytes


def load_opml_urls(path: Path) -> list[str]:
    """OPML 파일에서 URL 목록 추출"""
    if not path.exists():
        return []
    raw = path.read_bytes()
    # 깨진 & 교정
    raw = sanitize_opml_bytes(raw)
    root = ET.fromstring(raw)
    urls: list[str] = []
    seen = set()
    for o in root.iter("outline"):
        url = o.attrib.get("xmlUrl")
        if not url:
            continue
        nu = normalize_url(url)
        if nu in seen:
            continue
        seen.add(nu)
        urls.append(nu)
    return urls


def parse_opml_file(path: Path, *, blacklist: Set[str] | None = None) -> dict:
    """OPML 파일 파싱 및 피드 URL 추출"""
    blacklist = set(map(normalize_url, blacklist or set()))
    root = ET.parse(path).getroot()
    seen = set()
    urls = []
    for o in root.iter("outline"):
        url = o.attrib.get("xmlUrl")
        if not url:
            continue
        nu = normalize_url(url)
        if nu in blacklist or nu in seen:
            continue
        seen.add(nu)
        urls.append(nu)
    return {"urls": urls, "count": len(urls)}


def generate_opml(feed_urls: list[str]) -> str:
    """피드 URL 목록으로 OPML XML 생성"""
    urls = sorted(set(feed_urls))
    head = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0"><head>',
        '<title>Feeds Export</title>',
        '</head><body>'
    ]
    body = [f'<outline type="rss" text="{u}" title="{u}" xmlUrl="{u}" />' for u in urls]
    tail = ['</body></opml>']
    return "\n".join(head + body + tail)

