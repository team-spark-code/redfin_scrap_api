from datetime import datetime, timezone
from pydantic import BaseModel

from fastapi import FastAPI, Query, Body, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import BLACKLIST_FEEDS, BLACKLIST_DOMAINS
from app.rss_core import (
    init_feeds, update_all, add_discovered_feeds, 
    stats, mirror_entries_to_mongo, get_enabled_feeds,
    migrate_feeds_from_config
)
from app.repositories import FeedRepository
from api.feeds_routes import router as feeds_router 
from api.sync_routes import router as sync_router

app = FastAPI(
    title="RedFin RSS", 
    description="AI RSS News API Scrap Service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feeds_router)
app.include_router(sync_router)

class DiscoverIn(BaseModel):
    url: str
    top_k: int = 3

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/init")
def init():
    return init_feeds()

@app.post("/update", status_code=status.HTTP_202_ACCEPTED)
async def update(days: int = Query(1, ge=0), background_tasks: BackgroundTasks = BackgroundTasks()):
    """
    피드 업데이트 및 MongoDB 미러링 (비동기 백그라운드 실행)
    
    - days=0 이면 전체 미러링(=backfill)과 동일하게 동작
    - 기본 1일만 증분 미러링
    - 즉시 202 Accepted 응답 반환, 백그라운드에서 수집 수행
    """
    days_param = None if days == 0 else days
    background_tasks.add_task(update_all, days=days_param)
    return {
        "status": "accepted",
        "message": f"피드 업데이트가 백그라운드에서 시작되었습니다 (days={days_param or 'all'})",
        "days": days_param
    }

@app.post("/discover")
def discover(body: DiscoverIn):
    return add_discovered_feeds(url=body.url, top_k=body.top_k)

@app.get("/stats")
def get_stats(days: int = Query(7, ge=1, le=90)):
    return stats(days=days)

# 일회성 전체 백필
@app.post("/backfill")
def backfill(days: int | None = Query(None)):
    return mirror_entries_to_mongo(days=days)

@app.post("/backfill_range")
def backfill_range(start: str = Query(..., description="YYYY-MM-DD"),
                   end: str | None = Query(None, description="YYYY-MM-DD")):
    # 문자열 → UTC datetime
    s = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    e = datetime.fromisoformat(end).replace(tzinfo=timezone.utc) if end else datetime.now(timezone.utc)
    # mirror_entries_to_mongo가 days만 받는 구조라면,
    # 일수로 환산해서 넘기거나, 함수 내부에 start/end 지원을 추가하세요.
    days = int((datetime.now(timezone.utc) - s).total_seconds() // 86400)
    return mirror_entries_to_mongo(days=days)

# 블랙 리스트 관리
@app.get("/blacklist")
def list_blacklist():
    return {"feeds": sorted(BLACKLIST_FEEDS), "domains": sorted(BLACKLIST_DOMAINS)}

@app.post("/blacklist/feeds")
def add_blacklist_feed(url: str = Body(..., embed=True)):
    BLACKLIST_FEEDS.add(url); return {"ok": True, "feeds": sorted(BLACKLIST_FEEDS)}

@app.post("/blacklist/domains")
def add_blacklist_domain(domain: str = Body(..., embed=True)):
    BLACKLIST_DOMAINS.add(domain); return {"ok": True, "domains": sorted(BLACKLIST_DOMAINS)}

# 피드 관리 API
@app.get("/feeds")
def list_feeds(enabled: bool | None = Query(None, description="활성화 여부 필터 (None=전체)")):
    """피드 목록 조회"""
    feed_repo = FeedRepository()
    query = {}
    if enabled is not None:
        query["enabled"] = enabled
    
    feeds = list(feed_repo.collection.find(query, {"_id": 1, "title": 1, "site_url": 1, "enabled": 1}))
    return {
        "feeds": [
            {
                "url": f["_id"],
                "title": f.get("title"),
                "site_url": f.get("site_url"),
                "enabled": f.get("enabled", True)
            }
            for f in feeds
        ],
        "total": len(feeds)
    }

@app.post("/feeds")
def add_feed(url: str = Body(..., embed=True), title: str | None = Body(None, embed=True), enabled: bool = Body(True, embed=True)):
    """피드 추가"""
    feed_repo = FeedRepository()
    success = feed_repo.add_feed(url, title=title, enabled=enabled)
    return {"ok": success, "url": url, "message": "피드가 추가되었습니다" if success else "피드가 이미 존재합니다"}

@app.delete("/feeds/{url:path}")
def remove_feed(url: str):
    """피드 삭제"""
    feed_repo = FeedRepository()
    success = feed_repo.remove_feed(url)
    return {"ok": success, "url": url, "message": "피드가 삭제되었습니다" if success else "피드를 찾을 수 없습니다"}

@app.patch("/feeds/{url:path}")
def update_feed_enabled(url: str, enabled: bool = Body(..., embed=True)):
    """피드 활성화/비활성화"""
    feed_repo = FeedRepository()
    success = feed_repo.set_enabled(url, enabled)
    return {
        "ok": success,
        "url": url,
        "enabled": enabled,
        "message": f"피드가 {'활성화' if enabled else '비활성화'}되었습니다" if success else "피드를 찾을 수 없습니다"
    }

@app.post("/feeds/migrate")
def migrate_feeds():
    """기존 config.py의 AI_FEEDS를 MongoDB로 마이그레이션 (한 번만 실행)"""
    return migrate_feeds_from_config()
