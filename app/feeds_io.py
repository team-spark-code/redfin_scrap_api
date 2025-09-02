# app/feeds_io.py
from __future__ import annotations
import os, xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Set, Tuple
import yaml

from .config import PROJECT_ROOT
from .rss_core import _reader
from .urlnorm import normalize_url

BLACKLIST_PATH = PROJECT_ROOT / "data" / "blacklist.yaml"
FEEDS_PATH     = PROJECT_ROOT / "data" / "feeds.yaml"
OPML_PATH      = PROJECT_ROOT / "data" / "my_feeds.opml"

def load_blacklist_urls() -> Set[str]:
    urls: Set[str] = set()
    if BLACKLIST_PATH.exists():
        data = yaml.safe_load(BLACKLIST_PATH.read_text(encoding="utf-8"))
        items = data.get("items", []) if isinstance(data, dict) else []
        for it in items:
            u = (it.get("final_url") or it.get("url") or "").strip()
            if u:
                urls.add(normalize_url(u))
    return urls

def load_feeds_yaml() -> Tuple[list[dict], list[str]]:
    feeds = []
    urls: list[str] = []
    if FEEDS_PATH.exists():
        data = yaml.safe_load(FEEDS_PATH.read_text(encoding="utf-8"))
        seen = set()
        for it in data.get("feeds", []):
            u = it.get("url")
            if not u: continue
            nu = normalize_url(u)
            if nu in seen: continue
            seen.add(nu)
            feeds.append({**it, "url": nu})
            urls.append(nu)
    return feeds, urls

def load_opml_urls(path: Path | None = None) -> list[str]:
    p = path or OPML_PATH
    if not p.exists():
        return []
    from .urlnorm import sanitize_opml_bytes
    raw = p.read_bytes()
    # 깨진 & 교정
    raw = sanitize_opml_bytes(raw)
    root = ET.fromstring(raw)
    urls: list[str] = []
    seen = set()
    for o in root.iter("outline"):
        url = o.attrib.get("xmlUrl")
        if not url: continue
        nu = normalize_url(url)
        if nu in seen: continue
        seen.add(nu)
        urls.append(nu)
    return urls

def import_opml(path: Path, *, blacklist: Set[str] | None = None) -> dict:
    blacklist = set(map(normalize_url, blacklist or set()))
    r = _reader()
    added = skipped = 0
    root = ET.parse(path).getroot()
    seen = set()
    for o in root.iter("outline"):
        url = o.attrib.get("xmlUrl")
        if not url: continue
        nu = normalize_url(url)
        if nu in blacklist or nu in seen:
            skipped += 1; continue
        seen.add(nu)
        try:
            r.add_feed(nu); added += 1
        except Exception:
            skipped += 1
    r.update_feeds()
    return {"added": added, "skipped": skipped}

def export_opml(path: Path | None = None) -> str:
    r = _reader()
    urls = sorted({f.url for f in r.get_feeds()})
    head = ['<?xml version="1.0" encoding="UTF-8"?>','<opml version="2.0"><head>','<title>Feeds Export</title>','</head><body>']
    body = [f'<outline type="rss" text="{u}" title="{u}" xmlUrl="{u}" />' for u in urls]
    tail = ['</body></opml>']
    xml = "\n".join(head + body + tail)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(xml, encoding="utf-8")
    return xml

def sync_from_yaml(delete_missing: bool = False) -> dict:
    bl = load_blacklist_urls()
    _, want_urls = load_feeds_yaml()
    want = {u for u in want_urls if u not in bl}

    r = _reader()
    have = {f.url for f in r.get_feeds()}

    to_add = sorted(want - have)
    to_remove = sorted(have - want) if delete_missing else []

    a = d = 0
    for u in to_add:
        try: r.add_feed(u); a += 1
        except: pass
    for u in to_remove:
        try: r.delete_feed(u); d += 1
        except: pass
    r.update_feeds()
    return {"added": a, "removed": d, "kept": len(want & have)}
