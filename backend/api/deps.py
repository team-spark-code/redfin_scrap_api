# backend/api/deps.py
"""FastAPI 의존성 주입

FastAPI의 Depends를 위한 래퍼 함수들.
실제 객체 생성은 backend.core.container.Container에서 담당합니다.
"""
from backend.core.container import Container
from backend.repositories import FeedRepository, EntryRepository
from backend.services.crawler_service import CrawlerService
from backend.services.feed_service import FeedService


def get_feed_repository() -> FeedRepository:
    """FeedRepository 인스턴스 반환 (FastAPI Depends용)"""
    return Container.get_feed_repository()


def get_entry_repository() -> EntryRepository:
    """EntryRepository 인스턴스 반환 (FastAPI Depends용)"""
    return Container.get_entry_repository()


def get_crawler_service(
    feed_repo: FeedRepository | None = None,
    entry_repo: EntryRepository | None = None,
) -> CrawlerService:
    """CrawlerService 인스턴스 반환 (FastAPI Depends용)"""
    return Container.get_crawler_service(feed_repo=feed_repo, entry_repo=entry_repo)


def get_feed_service(feed_repo: FeedRepository | None = None) -> FeedService:
    """FeedService 인스턴스 반환 (FastAPI Depends용)"""
    return Container.get_feed_service(feed_repo=feed_repo)

