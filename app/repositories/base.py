# app/repositories/base.py
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict
from pymongo.database import Database
from .database import MongoManager


class BaseRepository(ABC):
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def db(self) -> Database:
        return MongoManager.get_db()

    @property
    def collection(self):
        return self.db[self.collection_name]

    @abstractmethod
    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def upsert_many(self, items: List[Dict[str, Any]]) -> int:
        """대량 삽입/수정 처리. 수정된/삽입된 개수 반환"""
        pass

