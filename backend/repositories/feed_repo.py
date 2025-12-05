# backend/repositories/feed_repo.py
from typing import List, Dict, Any, Optional
from pymongo import UpdateOne
from .base import BaseRepository


class FeedRepository(BaseRepository):
    def __init__(self):
        super().__init__("feeds")

    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"_id": id})

    def upsert_many(self, items: List[Dict[str, Any]]) -> int:
        """대량 삽입/수정 처리. 수정된/삽입된 개수 반환"""
        if not items:
            return 0

        ops = []
        for item in items:
            # item["_id"]가 반드시 존재해야 함
            ops.append(UpdateOne({"_id": item["_id"]}, {"$set": item}, upsert=True))

        # bulk_write 실행
        res = self.collection.bulk_write(ops, ordered=False)
        return res.upserted_count + res.modified_count

    def count(self) -> int:
        """feeds 컬렉션 문서 수 조회"""
        return self.collection.estimated_document_count()

    def create_indexes(self):
        """인덱스 생성 로직"""
        # _id는 기본적으로 unique 인덱스가 자동 생성됨
        # 필요시 추가 인덱스 생성 가능
        pass

    def get_enabled_feeds(self) -> List[str]:
        """활성화된 피드 URL 목록 반환"""
        feeds = self.collection.find(
            {"enabled": {"$ne": False}},  # enabled가 False가 아닌 모든 문서 (None도 포함)
            {"_id": 1}
        )
        return [feed["_id"] for feed in feeds]

    def add_feed(self, url: str, title: Optional[str] = None, site_url: Optional[str] = None, enabled: bool = True) -> bool:
        """피드 추가 (또는 업데이트)"""
        doc = {
            "title": title or url,
            "site_url": site_url or url,
            "enabled": enabled,
        }
        result = self.collection.update_one(
            {"_id": url},
            {"$set": doc, "$setOnInsert": {"enabled": enabled}},
            upsert=True
        )
        return result.upserted_count > 0 or result.modified_count > 0

    def remove_feed(self, url: str) -> bool:
        """피드 삭제"""
        result = self.collection.delete_one({"_id": url})
        return result.deleted_count > 0

    def set_enabled(self, url: str, enabled: bool) -> bool:
        """피드 활성화/비활성화"""
        result = self.collection.update_one(
            {"_id": url},
            {"$set": {"enabled": enabled}}
        )
        return result.modified_count > 0

    def bulk_upsert_feeds(self, feeds) -> Dict[str, Any]:
        """Reader feed 객체 리스트를 받아 MongoDB로 변환하여 upsert"""
        ops = []
        for f in feeds:
            url = getattr(f, "url", None)
            title = getattr(f, "title", None) or url
            site_url = getattr(f, "link", None) or url
            if not url:
                continue
            # 기존 문서가 있으면 enabled 필드는 유지, 없으면 기본값 True
            ops.append(UpdateOne(
                {"_id": url},
                {
                    "$set": {
                        "title": title,
                        "site_url": site_url,
                    },
                    "$setOnInsert": {"enabled": True}  # 새 문서일 때만 enabled=True 설정
                },
                upsert=True
            ))

        if ops:
            res = self.collection.bulk_write(ops, ordered=False)
            return {"feeds_upserted": res.upserted_count, "feeds_modified": res.modified_count}
        return {"feeds_upserted": 0, "feeds_modified": 0}

