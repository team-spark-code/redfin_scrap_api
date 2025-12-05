# backend/services/feed_service.py
"""피드 관리 서비스 (CRUD, OPML, Discover)"""
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import xml.etree.ElementTree as ET
import yaml
import requests
from bs4 import BeautifulSoup
from feedsearch import search as fs_search

from backend.repositories import FeedRepository
from backend.services.reader_service import ReaderService
from backend.core.config import PROJECT_ROOT, AI_FEEDS, BLACKLIST_FEEDS, BLACKLIST_DOMAINS
from backend.utils.url_norm import normalize_url, sanitize_opml_bytes
from backend.utils.opml_parser import load_opml_urls, parse_opml_file, generate_opml
from backend.core.exceptions import FeedNotFoundException, FeedAlreadyExistsException

logger = logging.getLogger(__name__)

BLACKLIST_PATH = PROJECT_ROOT / "data" / "blacklist.yaml"
FEEDS_PATH = PROJECT_ROOT / "data" / "feeds.yaml"
OPML_PATH = PROJECT_ROOT / "data" / "my_feeds.opml"


class FeedService:
    """피드 관리 서비스"""
    
    def __init__(self, feed_repo: Optional[FeedRepository] = None):
        self.feed_repo = feed_repo or FeedRepository()
        self.reader_service = ReaderService()

    def get_all_feeds(self, enabled: Optional[bool] = None) -> List[Dict[str, Any]]:
        """피드 목록 조회"""
        query = {}
        if enabled is not None:
            query["enabled"] = enabled
        
        feeds = list(self.feed_repo.collection.find(query, {"_id": 1, "title": 1, "site_url": 1, "enabled": 1}))
        return [
            {
                "url": f["_id"],
                "title": f.get("title"),
                "site_url": f.get("site_url"),
                "enabled": f.get("enabled", True)
            }
            for f in feeds
        ]

    def add_feed(self, url: str, title: Optional[str] = None, enabled: bool = True) -> Dict[str, Any]:
        """피드 추가"""
        success = self.feed_repo.add_feed(url, title=title, enabled=enabled)
        if not success:
            raise FeedAlreadyExistsException(f"피드가 이미 존재합니다: {url}")
        return {"ok": True, "url": url, "message": "피드가 추가되었습니다"}

    def remove_feed(self, url: str) -> Dict[str, Any]:
        """피드 삭제"""
        success = self.feed_repo.remove_feed(url)
        if not success:
            raise FeedNotFoundException(f"피드를 찾을 수 없습니다: {url}")
        return {"ok": True, "url": url, "message": "피드가 삭제되었습니다"}

    def update_feed_enabled(self, url: str, enabled: bool) -> Dict[str, Any]:
        """피드 활성화/비활성화"""
        success = self.feed_repo.set_enabled(url, enabled)
        if not success:
            raise FeedNotFoundException(f"피드를 찾을 수 없습니다: {url}")
        return {
            "ok": True,
            "url": url,
            "enabled": enabled,
            "message": f"피드가 {'활성화' if enabled else '비활성화'}되었습니다"
        }

    def migrate_feeds_from_config(self) -> Dict[str, Any]:
        """기존 config.py의 AI_FEEDS를 MongoDB로 마이그레이션"""
        added = 0
        skipped = 0
        
        for url in AI_FEEDS:
            try:
                if self.feed_repo.add_feed(url, enabled=True):
                    added += 1
                    logger.info(f"피드 마이그레이션: {url}")
                else:
                    skipped += 1
            except Exception as e:
                logger.warning(f"피드 마이그레이션 실패: {url} - {str(e)}")
                skipped += 1
        
        return {"migrated": added, "skipped": skipped, "total": len(AI_FEEDS)}

    def _discover_urls(self, url: str, top_k: int = 3) -> List[str]:
        """URL에서 RSS 피드 발견"""
        try:
            res = fs_search(url, max_urls=20, timeout=10)
            cands = [x.url for x in res][:top_k]
            if cands:
                return cands
        except Exception:
            pass
        try:
            html = requests.get(url, timeout=10).text
            soup = BeautifulSoup(html, "lxml")
            links = []
            for l in soup.find_all("link"):
                t = (l.get("type") or "").lower()
                if "rss" in t or "atom" in t or "xml" in t:
                    href = l.get("href")
                    if href:
                        links.append(href)
            return links[:top_k]
        except Exception:
            return []

    def discover_feeds(self, url: str, top_k: int = 3) -> Dict[str, Any]:
        """URL에서 RSS 피드 발견 및 Reader에 추가"""
        r = self.reader_service.get_reader()
        cands = self._discover_urls(url, top_k)
        added, skipped = 0, 0
        for u in cands:
            try:
                r.add_feed(u)
                added += 1
            except Exception:
                skipped += 1
        return {"source_url": url, "candidates": cands, "added": added, "skipped": skipped}

    def load_blacklist_urls(self) -> Set[str]:
        """블랙리스트 URL 로드"""
        urls: Set[str] = set()
        if BLACKLIST_PATH.exists():
            data = yaml.safe_load(BLACKLIST_PATH.read_text(encoding="utf-8"))
            items = data.get("items", []) if isinstance(data, dict) else []
            for it in items:
                u = (it.get("final_url") or it.get("url") or "").strip()
                if u:
                    urls.add(normalize_url(u))
        return urls

    def load_feeds_yaml(self) -> tuple[list[dict], list[str]]:
        """feeds.yaml 파일 로드"""
        feeds = []
        urls: list[str] = []
        if FEEDS_PATH.exists():
            data = yaml.safe_load(FEEDS_PATH.read_text(encoding="utf-8"))
            seen = set()
            for it in data.get("feeds", []):
                u = it.get("url")
                if not u:
                    continue
                nu = normalize_url(u)
                if nu in seen:
                    continue
                seen.add(nu)
                feeds.append({**it, "url": nu})
                urls.append(nu)
        return feeds, urls

    def import_opml(self, path: Path, *, blacklist: Set[str] | None = None) -> dict:
        """OPML 파일 import"""
        blacklist = set(map(normalize_url, blacklist or set()))
        r = self.reader_service.get_reader()
        added = skipped = 0
        root = ET.parse(path).getroot()
        seen = set()
        for o in root.iter("outline"):
            url = o.attrib.get("xmlUrl")
            if not url:
                continue
            nu = normalize_url(url)
            if nu in blacklist or nu in seen:
                skipped += 1
                continue
            seen.add(nu)
            try:
                r.add_feed(nu)
                added += 1
            except Exception:
                skipped += 1
        r.update_feeds()
        return {"added": added, "skipped": skipped}

    def export_opml(self) -> str:
        """현재 Reader 피드를 OPML로 내보내기"""
        r = self.reader_service.get_reader()
        urls = sorted({f.url for f in r.get_feeds()})
        return generate_opml(urls)

    def sync_from_yaml(self, delete_missing: bool = False) -> dict:
        """feeds.yaml과 Reader 동기화"""
        bl = self.load_blacklist_urls()
        _, want_urls = self.load_feeds_yaml()
        want = {u for u in want_urls if u not in bl}

        r = self.reader_service.get_reader()
        have = {f.url for f in r.get_feeds()}

        to_add = sorted(want - have)
        to_remove = sorted(have - want) if delete_missing else []

        a = d = 0
        for u in to_add:
            try:
                r.add_feed(u)
                a += 1
            except:
                pass
        for u in to_remove:
            try:
                r.delete_feed(u)
                d += 1
            except:
                pass
        r.update_feeds()
        return {"added": a, "removed": d, "kept": len(want & have)}

    def sync_feeds_to_mongo(self, delete_missing: bool = False) -> Dict[str, Any]:
        """feeds.yaml + OPML을 MongoDB와 동기화"""
        feeds_yaml, urls_yaml = self.load_feeds_yaml()
        urls_opml = load_opml_urls(OPML_PATH)
        bl = self.load_blacklist_urls()
        wanted: Set[str] = {normalize_url(u) for u in (urls_yaml + urls_opml) if u}
        wanted = {u for u in wanted if u not in bl}

        current = set(d["_id"] for d in self.feed_repo.collection.find({}, {"_id": 1}))

        to_add = sorted(wanted - current)
        to_remove = sorted(current - wanted) if delete_missing else []

        # upsert
        from pymongo import UpdateOne
        ops = []
        for u in to_add:
            ops.append(UpdateOne({"_id": u}, {"$set": {"title": u, "site_url": u, "enabled": True}}, upsert=True))
        upserted = modified = 0
        if ops:
            res = self.feed_repo.collection.bulk_write(ops, ordered=False)
            upserted = res.upserted_count
            modified = res.modified_count

        # delete (옵션)
        deleted = 0
        if to_remove:
            r = self.feed_repo.collection.delete_many({"_id": {"$in": to_remove}})
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

