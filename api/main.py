from datetime import datetime, timezone
from pydantic import BaseModel

from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware

from app.config import BLACKLIST_FEEDS, BLACKLIST_DOMAINS
from app.rss_core import (
    init_feeds, update_all, add_discovered_feeds, 
    stats, mirror_entries_to_mongo
)
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
    allow_origins=["http://localhost:3001"],
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

@app.post("/update")
def update(days: int = Query(1, ge=0)):
    """
    days=0 이면 전체 미러링(=backfill)과 동일하게 동작
    기본 1일만 증분 미러링
    """
    return update_all(days=None if days == 0 else days)

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
