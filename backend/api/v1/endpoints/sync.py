# backend/api/v1/endpoints/sync.py
"""동기화 API 엔드포인트"""
from fastapi import APIRouter, Body, Depends
from typing import Dict, Any

from backend.services.feed_service import FeedService
from backend.api.deps import get_feed_service

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/feeds", summary="SOT(feeds.yaml + my_feeds.opml) ↔ MongoDB(redfin.feeds) 동기화")
def sync_feeds(
    delete_missing: bool = Body(False, embed=True),
    service: FeedService = Depends(get_feed_service)
) -> Dict[str, Any]:
    """SOT(feeds.yaml + my_feeds.opml) ↔ MongoDB(redfin.feeds) 동기화"""
    return service.sync_feeds_to_mongo(delete_missing=delete_missing)

