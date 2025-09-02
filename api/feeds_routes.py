from __future__ import annotations
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Body, HTTPException
from fastapi.responses import Response
from app.feeds_io import (
    load_blacklist_urls, load_feeds_yaml,
    import_opml as _import_opml_stub, export_opml,
    export_opml, sync_from_yaml,
)
from app.config import PROJECT_ROOT
from app.rss_core import _reader
from app.rss_core import _reader, mirror_feeds_to_mongo
from app.urlnorm import sanitize_opml_bytes
import xml.etree.ElementTree as ET

router = APIRouter(prefix="/feeds", tags=["feeds"])

@router.get("", summary="현재 Reader에 등록된 피드 열람")
def list_feeds():
    r = _reader()
    return [{"url": f.url, "title": getattr(f, "title", None)} for f in r.get_feeds()]

@router.post("/import-opml", summary="OPML 업로드 등록(블랙리스트/정규화/자동교정)")
async def import_opml_api(file: UploadFile = File(...), mirror: bool = True):
    raw = await file.read()
    # 깨진 '&' 자동 교정
    raw = sanitize_opml_bytes(raw)
    try:
        ET.fromstring(raw)  # 유효성 간단 검증
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid OPML: {e}")

    with tempfile.NamedTemporaryFile(suffix=".opml", delete=True) as tmp:
        tmp.write(raw); tmp.flush()
        res = _import_opml_stub(Path(tmp.name), blacklist=load_blacklist_urls())

    if mirror:
        try:
            res["mongo"] = mirror_feeds_to_mongo()
        except Exception as e:
            res["mongo_error"] = str(e)
    return res

@router.get("/export-opml", summary="현재 Reader 피드를 OPML로 내보내기", response_class=Response)
def export_opml_api(download: bool = False):
    xml = export_opml()  # 파일 저장 없이 문자열 반환
    headers = {}
    if download:
        headers["Content-Disposition"] = 'attachment; filename="feeds_export.opml"'
    return Response(content=xml, media_type="application/xml", headers=headers)

@router.post("/sync", summary="feeds.yaml ↔ Reader 동기화(블랙리스트 적용)")
def sync_yaml_api(delete_missing: bool = Body(False, embed=True)):
    return sync_from_yaml(delete_missing=delete_missing)

@router.get("/sources", summary="feeds.yaml / blacklist.yaml 내용 확인")
def sources_view():
    feeds, urls = load_feeds_yaml()
    bl = sorted(load_blacklist_urls())
    return {"feeds_yaml_count": len(feeds), "feeds_yaml_urls": urls, "blacklist_count": len(bl), "blacklist_urls": bl}

@router.post("/mirror-to-mongo", summary="Reader의 feed 목록을 MongoDB feeds 컬렉션으로 동기화")
def mirror_to_mongo():
    return mirror_feeds_to_mongo()
