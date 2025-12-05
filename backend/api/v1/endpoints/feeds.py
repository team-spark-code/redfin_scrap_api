# backend/api/v1/endpoints/feeds.py
"""피드 관리 API 엔드포인트"""
from __future__ import annotations
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Body, Query, Depends, HTTPException
from fastapi.responses import Response
import xml.etree.ElementTree as ET

from backend.services.feed_service import FeedService
from backend.api.deps import get_feed_service
from backend.schemas.feed import (
    FeedResponse, FeedListResponse, FeedCreate, FeedOperationResponse
)
from backend.schemas.common import MigrateResponse
from backend.utils.url_norm import sanitize_opml_bytes
from backend.core.exceptions import FeedNotFoundException, FeedAlreadyExistsException

router = APIRouter(prefix="/feeds", tags=["feeds"])


@router.get("", response_model=FeedListResponse, summary="피드 목록 조회")
def list_feeds(
    enabled: bool | None = Query(None, description="활성화 여부 필터 (None=전체)"),
    service: FeedService = Depends(get_feed_service)
):
    """피드 목록 조회"""
    feeds = service.get_all_feeds(enabled=enabled)
    return {
        "feeds": [FeedResponse(**f) for f in feeds],
        "total": len(feeds)
    }


@router.post("", response_model=FeedOperationResponse, summary="피드 추가")
def add_feed(
    feed: FeedCreate,
    service: FeedService = Depends(get_feed_service)
):
    """피드 추가"""
    try:
        return service.add_feed(feed.url, title=feed.title, enabled=feed.enabled)
    except FeedAlreadyExistsException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{url:path}", response_model=FeedOperationResponse, summary="피드 삭제")
def remove_feed(
    url: str,
    service: FeedService = Depends(get_feed_service)
):
    """피드 삭제"""
    try:
        return service.remove_feed(url)
    except FeedNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{url:path}", response_model=FeedOperationResponse, summary="피드 활성화/비활성화")
def update_feed_enabled(
    url: str,
    enabled: bool = Body(..., embed=True),
    service: FeedService = Depends(get_feed_service)
):
    """피드 활성화/비활성화"""
    try:
        return service.update_feed_enabled(url, enabled)
    except FeedNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/migrate", response_model=MigrateResponse, summary="config.py 피드 마이그레이션")
def migrate_feeds(service: FeedService = Depends(get_feed_service)):
    """기존 config.py의 AI_FEEDS를 MongoDB로 마이그레이션 (한 번만 실행)"""
    return service.migrate_feeds_from_config()


@router.get("/reader", summary="현재 Reader에 등록된 피드 열람")
def list_reader_feeds(service: FeedService = Depends(get_feed_service)):
    """Reader에 등록된 피드 목록"""
    from backend.services.reader_service import ReaderService
    r = ReaderService.get_reader()
    return [{"url": f.url, "title": getattr(f, "title", None)} for f in r.get_feeds()]


@router.post("/import-opml", summary="OPML 업로드 등록")
async def import_opml_api(
    file: UploadFile = File(...),
    mirror: bool = True,
    service: FeedService = Depends(get_feed_service)
):
    """OPML 업로드 등록(블랙리스트/정규화/자동교정)"""
    raw = await file.read()
    # 깨진 '&' 자동 교정
    raw = sanitize_opml_bytes(raw)
    try:
        ET.fromstring(raw)  # 유효성 간단 검증
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid OPML: {e}")

    with tempfile.NamedTemporaryFile(suffix=".opml", delete=True) as tmp:
        tmp.write(raw)
        tmp.flush()
        res = service.import_opml(Path(tmp.name), blacklist=service.load_blacklist_urls())

    if mirror:
        try:
            from backend.services.crawler_service import CrawlerService
            crawler = CrawlerService()
            res["mongo"] = crawler.mirror_feeds_to_mongo()
        except Exception as e:
            res["mongo_error"] = str(e)
    return res


@router.get("/export-opml", summary="현재 Reader 피드를 OPML로 내보내기", response_class=Response)
def export_opml_api(
    download: bool = False,
    service: FeedService = Depends(get_feed_service)
):
    """현재 Reader 피드를 OPML로 내보내기"""
    xml = service.export_opml()
    headers = {}
    if download:
        headers["Content-Disposition"] = 'attachment; filename="feeds_export.opml"'
    return Response(content=xml, media_type="application/xml", headers=headers)


@router.post("/sync", summary="feeds.yaml ↔ Reader 동기화")
def sync_yaml_api(
    delete_missing: bool = Body(False, embed=True),
    service: FeedService = Depends(get_feed_service)
):
    """feeds.yaml ↔ Reader 동기화(블랙리스트 적용)"""
    return service.sync_from_yaml(delete_missing=delete_missing)


@router.get("/sources", summary="feeds.yaml / blacklist.yaml 내용 확인")
def sources_view(service: FeedService = Depends(get_feed_service)):
    """feeds.yaml / blacklist.yaml 내용 확인"""
    feeds, urls = service.load_feeds_yaml()
    bl = sorted(service.load_blacklist_urls())
    return {
        "feeds_yaml_count": len(feeds),
        "feeds_yaml_urls": urls,
        "blacklist_count": len(bl),
        "blacklist_urls": bl
    }


@router.post("/mirror-to-mongo", summary="Reader의 feed 목록을 MongoDB feeds 컬렉션으로 동기화")
def mirror_to_mongo(service: FeedService = Depends(get_feed_service)):
    """Reader의 feed 목록을 MongoDB feeds 컬렉션으로 동기화"""
    from backend.api.deps import get_crawler_service
    crawler = get_crawler_service()
    return crawler.mirror_feeds_to_mongo()

