# backend/schemas/feed.py
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional


class FeedBase(BaseModel):
    url: str = Field(..., description="피드 URL")
    title: Optional[str] = Field(None, description="피드 제목")
    site_url: Optional[str] = Field(None, description="사이트 URL")


class FeedCreate(FeedBase):
    enabled: bool = Field(True, description="활성화 여부")


class FeedUpdate(BaseModel):
    title: Optional[str] = None
    site_url: Optional[str] = None
    enabled: Optional[bool] = None


class FeedResponse(FeedBase):
    enabled: bool = Field(True, description="활성화 여부")

    class Config:
        from_attributes = True


class FeedListResponse(BaseModel):
    feeds: list[FeedResponse]
    total: int


class FeedOperationResponse(BaseModel):
    ok: bool
    url: str
    message: str
    enabled: Optional[bool] = None

