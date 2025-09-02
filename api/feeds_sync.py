from fastapi import APIRouter, UploadFile, File, Body
from app.rss_core import _reader
from .deps import BLACKLIST_URLS  # blacklist.yaml 로딩 결과라고 가정
import xml.etree.ElementTree as ET

router = APIRouter(prefix="/feeds", tags=["feeds"])

@router.post("/import-opml")
async def import_opml(file: UploadFile = File(...)):
    data = await file.read()
    root = ET.fromstring(data)
    r = _reader()
    added = skipped = 0
    for o in root.iter("outline"):
        url = o.attrib.get("xmlUrl")
        if not url or url in BLACKLIST_URLS: 
            skipped += 1; continue
        try: r.add_feed(url); added += 1
        except Exception: skipped += 1
    r.update_feeds()
    return {"added": added, "skipped": skipped}

@router.get("/export-opml")
def export_opml():
    r = _reader()
    urls = sorted({f.url for f in r.get_feeds()})
    # OPML 문자열 생성
    from datetime import datetime
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<opml version="2.0"><head>',
            f'<title>Feeds Export</title>',
            '</head><body>']
    for u in urls:
        body.append(f'<outline type="rss" text="{u}" title="{u}" xmlUrl="{u}"/>')
    body.append('</body></opml>')
    return {"opml": "\n".join(body)}

@router.post("/sync")
def sync(from_yaml: list[str] = Body(..., embed=True), delete_missing: bool = False):
    """from_yaml: feeds.yaml에서 읽어온 URL 배열을 전달.
       delete_missing=True면 Reader에만 있는 URL을 제거."""
    r = _reader()
    wanted = {u for u in from_yaml if u not in BLACKLIST_URLS}
    current = {f.url for f in r.get_feeds()}
    to_add = sorted(wanted - current)
    to_remove = sorted(current - wanted) if delete_missing else []
    added = removed = 0
    for u in to_add:
        try: r.add_feed(u); added += 1
        except: pass
    if removed:
        for u in to_remove:
            try: r.delete_feed(u); removed += 1
            except: pass
    r.update_feeds()
    return {"added": added, "removed": removed, "kept": len(wanted & current)}