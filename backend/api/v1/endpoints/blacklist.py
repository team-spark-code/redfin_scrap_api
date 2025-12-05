# backend/api/v1/endpoints/blacklist.py
"""블랙리스트 관리 API 엔드포인트"""
from fastapi import APIRouter, Body
from backend.core.config import BLACKLIST_FEEDS, BLACKLIST_DOMAINS

router = APIRouter(prefix="/blacklist", tags=["blacklist"])


@router.get("", summary="블랙리스트 조회")
def list_blacklist():
    """블랙리스트 조회"""
    return {"feeds": sorted(BLACKLIST_FEEDS), "domains": sorted(BLACKLIST_DOMAINS)}


@router.post("/feeds", summary="피드 블랙리스트 추가")
def add_blacklist_feed(url: str = Body(..., embed=True)):
    """피드 블랙리스트 추가"""
    BLACKLIST_FEEDS.add(url)
    return {"ok": True, "feeds": sorted(BLACKLIST_FEEDS)}


@router.post("/domains", summary="도메인 블랙리스트 추가")
def add_blacklist_domain(domain: str = Body(..., embed=True)):
    """도메인 블랙리스트 추가"""
    BLACKLIST_DOMAINS.add(domain)
    return {"ok": True, "domains": sorted(BLACKLIST_DOMAINS)}

