# backend/services/reader_service.py
"""Reader 라이브러리 래퍼 서비스"""
from reader import make_reader
from backend.core.config import RSS_DB_PATH


class ReaderService:
    """Reader 인스턴스 관리"""
    _instance = None

    @classmethod
    def get_reader(cls):
        """Reader 인스턴스 반환 (싱글톤)"""
        if cls._instance is None:
            cls._instance = make_reader(RSS_DB_PATH)
        return cls._instance

