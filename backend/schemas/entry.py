# backend/schemas/entry.py
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime


class EntryResponse(BaseModel):
    id: str
    feed_url: str
    title: Optional[str] = None
    link: Optional[str] = None
    published: Optional[datetime] = None
    domain: Optional[str] = None

    class Config:
        from_attributes = True


class DomainStats(BaseModel):
    domain: str
    count: int


class FeedStats(BaseModel):
    feed_url: str
    feed_title: str
    total: int
    recent_7d: Optional[int] = Field(None, alias="recent_7d")
    recent_30d: Optional[int] = Field(None, alias="recent_30d")

    class Config:
        populate_by_name = True


class StatsResponse(BaseModel):
    generated_at: str
    days: int
    feeds: int
    entries_total: int
    entries_recent: int
    domains_top10: list[DomainStats]
    weekday_dist: Dict[str, int]
    by_feed: list[FeedStats]
    date_range: Dict[str, Optional[str]]

