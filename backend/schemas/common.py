# backend/schemas/common.py
from pydantic import BaseModel
from typing import Optional, Dict, Any


class MessageResponse(BaseModel):
    message: str
    status: Optional[str] = None


class HealthResponse(BaseModel):
    ok: bool


class DiscoverRequest(BaseModel):
    url: str
    top_k: int = 3


class DiscoverResponse(BaseModel):
    source_url: str
    candidates: list[str]
    added: int
    skipped: int


class InitResponse(BaseModel):
    added: int
    skipped: int
    update_sec: float
    mongo_entries: Dict[str, Any]
    mongo_feeds: Dict[str, Any]


class UpdateResponse(BaseModel):
    status: str
    message: str
    days: Optional[int] = None


class MigrateResponse(BaseModel):
    migrated: int
    skipped: int
    total: int

