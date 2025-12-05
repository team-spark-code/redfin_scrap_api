# backend/api/deps.py
"""FastAPI 의존성 주입"""
from backend.repositories import FeedRepository, EntryRepository
from backend.services.crawler_service import CrawlerService
from backend.services.feed_service import FeedService


def get_feed_repository() -> FeedRepository:
    """FeedRepository 인스턴스 반환"""
    return FeedRepository()


def get_entry_repository() -> EntryRepository:
    """EntryRepository 인스턴스 반환"""
    return EntryRepository()


def get_crawler_service(
    feed_repo: FeedRepository | None = None,
    entry_repo: EntryRepository | None = None,
) -> CrawlerService:
    """CrawlerService 인스턴스 반환"""
    if feed_repo is None:
        feed_repo = get_feed_repository()
    if entry_repo is None:
        entry_repo = get_entry_repository()
    return CrawlerService(feed_repo=feed_repo, entry_repo=entry_repo)


def get_feed_service(feed_repo: FeedRepository | None = None) -> FeedService:
    """FeedService 인스턴스 반환"""
    if feed_repo is None:
        feed_repo = get_feed_repository()
    return FeedService(feed_repo=feed_repo)

