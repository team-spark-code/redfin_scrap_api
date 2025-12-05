# backend/api/v1/api.py
"""API v1 라우터 통합"""
from fastapi import APIRouter

from backend.api.v1.endpoints import feeds, sync, admin, blacklist

api_router = APIRouter()

api_router.include_router(feeds.router)
api_router.include_router(sync.router)
api_router.include_router(admin.router)
api_router.include_router(blacklist.router)

