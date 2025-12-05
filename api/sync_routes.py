from __future__ import annotations
from fastapi import APIRouter, Body
from typing import Dict, Any, Set
from pymongo import UpdateOne
from app.feeds_io import load_feeds_yaml, load_opml_urls, load_blacklist_urls
from app.urlnorm import normalize_url
from app.repositories.database import MongoManager

router = APIRouter(tags=["sync"])

def _mdb():
    """MongoDB 데이터베이스 인스턴스 반환 (인덱스 생성 없음)"""
    return MongoManager.get_db()

@router.post("/sync_feeds", summary="SOT(feeds.yaml + my_feeds.opml) ↔ MongoDB(redfin.feeds) 동기화")
def sync_feeds(delete_missing: bool = Body(False, embed=True)) -> Dict[str, Any]:
    # 1) SOT 수집: feeds.yaml + (있으면) my_feeds.opml
    feeds_yaml, urls_yaml = load_feeds_yaml()
    urls_opml = load_opml_urls()  # 존재하지 않으면 []
    # 2) 합집합 + 정규화 + 블랙리스트 제외
    bl: Set[str] = load_blacklist_urls()
    wanted: Set[str] = {normalize_url(u) for u in (urls_yaml + urls_opml) if u}
    wanted = {u for u in wanted if u not in bl}

    db = _mdb()
    current = set(d["_id"] for d in db.feeds.find({}, {"_id": 1}))

    to_add = sorted(wanted - current)
    to_remove = sorted(current - wanted) if delete_missing else []

    # 3) upsert
    ops = []
    for u in to_add:
        ops.append(UpdateOne({"_id": u}, {"$set": {"title": u, "site_url": u}}, upsert=True))
    upserted = modified = 0
    if ops:
        res = db.feeds.bulk_write(ops, ordered=False)
        upserted = res.upserted_count
        modified = res.modified_count

    # 4) delete (옵션)
    deleted = 0
    if to_remove:
        r = db.feeds.delete_many({"_id": {"$in": to_remove}})
        deleted = r.deleted_count

    return {
        "source": {
            "feeds_yaml": len(urls_yaml),
            "opml_urls": len(urls_opml),
            "blacklist": len(bl),
        },
        "wanted_total": len(wanted),
        "added": upserted,
        "modified": modified,
        "deleted": deleted,
        "kept": len(wanted & current),
    }
