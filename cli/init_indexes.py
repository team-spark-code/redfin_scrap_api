#!/usr/bin/env python3
"""
MongoDB 인덱스 초기화 스크립트

이 스크립트는 MongoDB 컬렉션에 필요한 인덱스를 생성합니다.
앱 시작 시 자동으로 실행되지 않으므로, 초기 설정 시 한 번만 실행하면 됩니다.

사용법:
    python -m cli.init_indexes
    또는
    python cli/init_indexes.py
"""
import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from backend.repositories import EntryRepository, FeedRepository
from backend.core.database import MongoManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_all_indexes():
    """모든 컬렉션의 인덱스 생성"""
    logger.info("MongoDB 인덱스 초기화 시작...")
    
    try:
        # EntryRepository 인덱스 생성
        logger.info("entries 컬렉션 인덱스 생성 중...")
        entry_repo = EntryRepository()
        entry_repo.create_indexes()
        logger.info("entries 컬렉션 인덱스 생성 완료")
        
        # FeedRepository 인덱스 생성
        logger.info("feeds 컬렉션 인덱스 생성 중...")
        feed_repo = FeedRepository()
        feed_repo.create_indexes()
        logger.info("feeds 컬렉션 인덱스 생성 완료")
        
        logger.info("모든 인덱스 초기화 완료")
        return True
        
    except Exception as e:
        logger.error(f"인덱스 초기화 실패: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = init_all_indexes()
    sys.exit(0 if success else 1)

