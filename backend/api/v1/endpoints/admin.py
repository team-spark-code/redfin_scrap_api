# backend/api/v1/endpoints/admin.py
"""관리자 API 엔드포인트 (초기화, 업데이트, 통계 등)"""
from datetime import datetime, timezone
from fastapi import APIRouter, Query, BackgroundTasks, status, Depends
from typing import Optional

from backend.services.crawler_service import CrawlerService
from backend.services.feed_service import FeedService
from backend.api.deps import get_crawler_service, get_feed_service
from backend.schemas.common import (
    HealthResponse, InitResponse, UpdateResponse, DiscoverRequest, DiscoverResponse
)
from backend.schemas.entry import StatsResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health", response_model=HealthResponse, summary="헬스체크")
def health():
    """헬스체크"""
    return {"ok": True}


@router.post("/init", response_model=InitResponse, summary="초기화")
def init(service: CrawlerService = Depends(get_crawler_service)):
    """MongoDB에서 활성화된 피드를 Reader에 등록하고 업데이트"""
    return service.init_feeds()


@router.post("/update", status_code=status.HTTP_202_ACCEPTED, response_model=UpdateResponse, summary="피드 업데이트")
async def update(
    days: int = Query(1, ge=0),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: CrawlerService = Depends(get_crawler_service)
):
    """
    피드 업데이트 및 MongoDB 미러링 (비동기 백그라운드 실행)
    
    - days=0 이면 전체 미러링(=backfill)과 동일하게 동작
    - 기본 1일만 증분 미러링
    - 즉시 202 Accepted 응답 반환, 백그라운드에서 수집 수행
    """
    days_param = None if days == 0 else days
    background_tasks.add_task(service.update_all, days=days_param)
    return {
        "status": "accepted",
        "message": f"피드 업데이트가 백그라운드에서 시작되었습니다 (days={days_param or 'all'})",
        "days": days_param
    }


@router.post("/discover", response_model=DiscoverResponse, summary="피드 발견")
def discover(
    body: DiscoverRequest,
    service: FeedService = Depends(get_feed_service)
):
    """URL에서 RSS 피드 발견 및 추가"""
    return service.discover_feeds(body.url, top_k=body.top_k)


@router.get("/stats", response_model=StatsResponse, summary="통계 조회")
def get_stats(
    days: int = Query(7, ge=1, le=90),
    service: CrawlerService = Depends(get_crawler_service)
):
    """통계 조회"""
    return service.get_stats(days=days)


@router.post("/backfill", summary="전체 백필")
def backfill(
    days: Optional[int] = Query(None),
    service: CrawlerService = Depends(get_crawler_service)
):
    """일회성 전체 백필"""
    return service.mirror_entries_to_mongo(days=days)


@router.post("/backfill_range", summary="기간별 백필")
def backfill_range(
    start: str = Query(..., description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    service: CrawlerService = Depends(get_crawler_service)
):
    """기간별 백필"""
    # 문자열 → UTC datetime
    s = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    e = datetime.fromisoformat(end).replace(tzinfo=timezone.utc) if end else datetime.now(timezone.utc)
    # 일수로 환산
    days = int((datetime.now(timezone.utc) - s).total_seconds() // 86400)
    return service.mirror_entries_to_mongo(days=days)

