# backend/repositories/entry_repo.py
from typing import List, Dict, Any, Optional, Tuple
from pymongo import UpdateOne
from .base import BaseRepository


class EntryRepository(BaseRepository):
    def __init__(self):
        super().__init__("entries")

    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"_id": id})

    def upsert_many(self, items: List[Dict[str, Any]], batch_size: int = 1000) -> int:
        """대량 삽입/수정 처리. 1000개 단위로 배치 처리. 수정된/삽입된 개수 반환"""
        if not items:
            return 0

        total_upserted = 0
        total_modified = 0

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            ops = []
            for item in batch:
                # item["_id"]가 반드시 존재해야 함
                ops.append(UpdateOne({"_id": item["_id"]}, {"$set": item}, upsert=True))

            if ops:
                res = self.collection.bulk_write(ops, ordered=False)
                total_upserted += res.upserted_count
                total_modified += res.modified_count

        return total_upserted + total_modified

    def estimated_count(self) -> int:
        """entries 컬렉션 예상 문서 수"""
        return self.collection.estimated_document_count()

    def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """aggregation 파이프라인 실행"""
        return list(self.collection.aggregate(pipeline))

    def find_one(self, filter: Optional[Dict[str, Any]] = None, sort: Optional[List[Tuple[str, int]]] = None) -> Optional[Dict[str, Any]]:
        """단일 문서 조회 (정렬 옵션 포함)"""
        if filter is None:
            filter = {}
        return self.collection.find_one(filter, sort=sort)

    def create_indexes(self):
        """인덱스 생성 로직"""
        self.collection.create_index([("feed_url", 1), ("published", -1)])
        self.collection.create_index([("domain", 1), ("published", -1)])
        self.collection.create_index([("published", -1)])

