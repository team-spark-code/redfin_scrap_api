# backend/core/container.py
"""
의존성 컨테이너 (Dependency Container)

Clean Architecture 원칙에 따라 객체 생성 로직을 중앙화합니다.
API와 CLI 모두 이 컨테이너를 통해 서비스를 생성합니다.
"""
from typing import Optional

from backend.repositories import FeedRepository, EntryRepository
from backend.services.crawler_service import CrawlerService
from backend.services.feed_service import FeedService


class Container:
    """의존성 컨테이너 - 서비스 인스턴스 생성 및 관리"""
    
    @staticmethod
    def get_feed_repository() -> FeedRepository:
        """FeedRepository 인스턴스 반환"""
        return FeedRepository()
    
    @staticmethod
    def get_entry_repository() -> EntryRepository:
        """EntryRepository 인스턴스 반환"""
        return EntryRepository()
    
    @staticmethod
    def get_crawler_service(
        feed_repo: Optional[FeedRepository] = None,
        entry_repo: Optional[EntryRepository] = None,
    ) -> CrawlerService:
        """CrawlerService 인스턴스 반환"""
        if feed_repo is None:
            feed_repo = Container.get_feed_repository()
        if entry_repo is None:
            entry_repo = Container.get_entry_repository()
        return CrawlerService(feed_repo=feed_repo, entry_repo=entry_repo)
    
    @staticmethod
    def get_feed_service(feed_repo: Optional[FeedRepository] = None) -> FeedService:
        """FeedService 인스턴스 반환"""
        if feed_repo is None:
            feed_repo = Container.get_feed_repository()
        return FeedService(feed_repo=feed_repo)

