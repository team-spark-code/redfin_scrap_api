from __future__ import annotations
from dotenv import load_dotenv ; load_dotenv()
import hashlib
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from inspect import signature
import requests
from bs4 import BeautifulSoup
from feedsearch import search as fs_search
from reader import make_reader

from .config import RSS_DB_PATH, BLACKLIST_FEEDS, BLACKLIST_DOMAINS, AI_FEEDS
from .agg_queries import pipeline_recent_count, pipeline_domains_top, pipeline_by_feed, pipeline_weekday_dist
from .repositories import FeedRepository, EntryRepository

# 로깅 설정
logger = logging.getLogger(__name__)

# ---------- Config ----------
MIRROR_ENABLED = os.getenv("MIRROR_ENABLED", "1") == "1"

# ---------- Helpers ----------
def _supports_newer_than(r) -> bool:
    try:
        return "newer_than" in signature(r.get_entries).parameters
    except Exception:
        return False

def _to_ts(v):
    """timestamp(float) 또는 datetime -> float(UTC seconds)"""
    dt = _to_dt(v)
    return dt.timestamp() if dt else None

def _blocked(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        p = urlparse(url)
        return url in BLACKLIST_FEEDS or (p.netloc in BLACKLIST_DOMAINS)
    except Exception:
        return False

# ---------- Reader ----------
def _reader():
    return make_reader(RSS_DB_PATH)

# ---------- Init & Update ----------
def migrate_feeds_from_config() -> Dict[str, Any]:
    """기존 config.py의 AI_FEEDS를 MongoDB로 마이그레이션 (한 번만 실행)"""
    feed_repo = FeedRepository()
    added = 0
    skipped = 0
    
    for url in AI_FEEDS:
        try:
            if feed_repo.add_feed(url, enabled=True):
                added += 1
                logger.info(f"피드 마이그레이션: {url}")
            else:
                skipped += 1
        except Exception as e:
            logger.warning(f"피드 마이그레이션 실패: {url} - {str(e)}")
            skipped += 1
    
    return {"migrated": added, "skipped": skipped, "total": len(AI_FEEDS)}

def get_enabled_feeds() -> List[str]:
    """MongoDB에서 활성화된 피드 목록 가져오기"""
    feed_repo = FeedRepository()
    return feed_repo.get_enabled_feeds()

def init_feeds() -> Dict[str, Any]:
    """MongoDB에서 활성화된 피드를 Reader에 등록하고 업데이트"""
    r = _reader()
    feed_repo = FeedRepository()
    
    # MongoDB에서 활성화된 피드 목록 가져오기
    enabled_feeds = feed_repo.get_enabled_feeds()
    logger.info(f"MongoDB에서 활성화된 피드 {len(enabled_feeds)}개 발견")
    
    added, skipped = 0, 0
    for url in enabled_feeds:
        try:
            r.add_feed(url)
            added += 1
        except Exception as e:
            logger.warning(f"피드 추가 실패: {url} - {str(e)}")
            skipped += 1
    
    start = time.time()
    r.update_feeds()
    # 초기 미러 (최근 7일)
    try:
        me = mirror_entries_to_mongo(days=7)
    except Exception as e:
        me = {"skipped": True, "reason": str(e)}
    try:
        mf = mirror_feeds_to_mongo()
    except Exception as e:
        mf = {"skipped": True, "reason": str(e)}
        # mf = mirror_feeds_to_mongo()
    return {"added": added, "skipped": skipped, "update_sec": round(time.time() - start, 2), "mongo_entries": me, "mongo_feeds": mf}

def sync_feeds_to_reader() -> Dict[str, Any]:
    """MongoDB의 활성화된 피드를 Reader와 동기화"""
    r = _reader()
    feed_repo = FeedRepository()
    
    # MongoDB에서 활성화된 피드 목록
    enabled_feeds = set(feed_repo.get_enabled_feeds())
    logger.info(f"MongoDB 활성화 피드: {len(enabled_feeds)}개")
    
    # Reader에 등록된 피드 목록
    reader_feeds = {f.url for f in r.get_feeds()}
    logger.info(f"Reader 등록 피드: {len(reader_feeds)}개")
    
    # 추가할 피드
    to_add = enabled_feeds - reader_feeds
    # 제거할 피드 (MongoDB에서 비활성화된 피드)
    to_remove = reader_feeds - enabled_feeds
    
    added, removed = 0, 0
    
    # 피드 추가
    for url in to_add:
        try:
            r.add_feed(url)
            added += 1
            logger.debug(f"피드 추가: {url}")
        except Exception as e:
            logger.warning(f"피드 추가 실패: {url} - {str(e)}")
    
    # 피드 제거
    for url in to_remove:
        try:
            r.delete_feed(url)
            removed += 1
            logger.debug(f"피드 제거: {url}")
        except Exception as e:
            logger.warning(f"피드 제거 실패: {url} - {str(e)}")
    
    if added > 0 or removed > 0:
        logger.info(f"피드 동기화 완료: 추가 {added}개, 제거 {removed}개")
    
    return {"added": added, "removed": removed, "total_enabled": len(enabled_feeds)}

def update_all(days: Optional[int] = 1) -> Dict[str, Any]:
    """피드 업데이트 및 MongoDB 미러링 (백그라운드 실행 가능)"""
    logger.info(f"피드 업데이트 시작 (days={days})")
    r = _reader()
    start = time.time()
    
    try:
        # MongoDB와 Reader 동기화
        sync_result = sync_feeds_to_reader()
        logger.info(f"피드 동기화: {sync_result}")
        
        logger.info("Reader 피드 업데이트 중...")
        r.update_feeds()
        logger.info("Reader 피드 업데이트 완료")
        
        logger.info(f"MongoDB 엔트리 미러링 시작 (days={days})...")
        me = mirror_entries_to_mongo(days=days)  # 증분 미러(기본 1일)
        elapsed = round(time.time() - start, 2)
        logger.info(f"피드 업데이트 완료 (소요 시간: {elapsed}초, 처리된 엔트리: {me.get('entries_processed', 0)})")
        
        return {
            "updated": True,
            "update_sec": elapsed,
            "mongo_entries": me,
            "feed_sync": sync_result
        }
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        logger.error(f"피드 업데이트 실패 (소요 시간: {elapsed}초): {str(e)}", exc_info=True)
        raise

# ---------- Discover ----------
def _discover_urls(url: str, top_k: int = 3) -> List[str]:
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

def add_discovered_feeds(url: str, top_k: int = 3) -> Dict[str, Any]:
    r = _reader()
    cands = _discover_urls(url, top_k)
    added, skipped = 0, 0
    for u in cands:
        try:
            r.add_feed(u)
            added += 1
        except Exception:
            skipped += 1
    return {"source_url": url, "candidates": cands, "added": added, "skipped": skipped}

# ---------- Mongo Mirror ----------
def _entry_key(e) -> str:
    if getattr(e, "id", None):
        return str(e.id)
    if getattr(e, "link", None):
        return str(e.link)
    base = f"{e.feed.url}|{getattr(e,'title',None)}|{getattr(e,'published',None)}"
    return hashlib.sha256(base.encode("utf-8", "ignore")).hexdigest()

def _to_dt(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, tz=timezone.utc)
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    return None

def mirror_feeds_to_mongo() -> Dict[str, Any]:
    """Reader의 feed 목록을 MongoDB redfin.feeds 컬렉션으로 upsert"""
    r = _reader()
    feed_repo = FeedRepository()
    return feed_repo.bulk_upsert_feeds(r.get_feeds())

def mirror_entries_to_mongo(days: Optional[int] = None) -> Dict[str, Any]:
    """Reader 엔트리를 MongoDB로 미러링"""
    r = _reader()
    entry_repo = EntryRepository()

    # 기간 기준 계산
    newer_ts = None
    if days:
        newer_ts = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
        logger.debug(f"기간 필터 적용: 최근 {days}일 (timestamp: {newer_ts})")

    # reader 버전에 따라 분기
    if newer_ts is not None and _supports_newer_than(r):
        it = r.get_entries(newer_than=newer_ts)  # 신버전 경로
        logger.debug("Reader 신버전 경로 사용 (newer_than 파라미터)")
    else:
        it = r.get_entries()  # 구버전 경로(수동 필터)
        logger.debug("Reader 구버전 경로 사용 (수동 필터)")

    docs = []
    processed_count = 0
    for e in it:
        # 구버전 경로일 때 수동 필터
        if newer_ts is not None and not _supports_newer_than(r):
            pub_ts = _to_ts(getattr(e, "published", None)) or _to_ts(getattr(e, "updated", None))
            if pub_ts is None or pub_ts < newer_ts:
                continue

        processed_count += 1
        _id = _entry_key(e)
        pub = _to_dt(getattr(e, "published", None)) or _to_dt(getattr(e, "updated", None))
        dom = None
        try:
            dom = urlparse(getattr(e, "link", "") or "").netloc or None
        except Exception:
            pass
        doc = {
            "_id": _id,
            "feed_url": e.feed.url,
            "title": getattr(e, "title", None),
            "link": getattr(e, "link", None),
            "published": pub,
            "updated": _to_dt(getattr(e, "updated", None)),
            "authors": getattr(e, "authors", None),
            "summary": getattr(e, "summary", None),
            "domain": dom,
            "mirrored_at": datetime.now(timezone.utc),
        }
        docs.append(doc)
        
        # 진행 상황 로깅 (1000개마다)
        if processed_count % 1000 == 0:
            logger.info(f"엔트리 처리 중: {processed_count}개 수집 완료...")

    logger.info(f"총 {len(docs)}개 엔트리 MongoDB 저장 시작...")
    # Repository의 upsert_many가 1000개 단위 배치 처리
    entry_repo.upsert_many(docs)
    logger.info(f"MongoDB 저장 완료: {len(docs)}개 엔트리")
    return {"entries_processed": len(docs)}

# ---------- Stats (Mongo Aggregation) ----------
def stats(days: int = 7) -> Dict[str, Any]:
    entry_repo = EntryRepository()
    feed_repo = FeedRepository()
    now = datetime.now(timezone.utc).isoformat()

    total = entry_repo.estimated_count()
    recent = entry_repo.aggregate(pipeline_recent_count(days))
    recent_cnt = recent[0]["recent"] if recent else 0

    domains = entry_repo.aggregate(pipeline_domains_top(days, 10))
    domains_out = [{"domain": d["_id"] or "(none)", "count": d["count"]} for d in domains]

    pipe_total, pipe_recent = pipeline_by_feed(days)
    total_by_feed = {d["_id"]: {"total": d["total"], "title": d.get("feed_title", d["_id"])}
                     for d in entry_repo.aggregate(pipe_total)}
    for d in entry_repo.aggregate(pipe_recent):
        total_by_feed.setdefault(d["_id"], {"total": 0, "title": d["_id"]})
        total_by_feed[d["_id"]]["recent"] = d["recent"]

    # 요일 분포
    wd = entry_repo.aggregate(pipeline_weekday_dist())
    weekday_dist = {str(item["_id"]): item["count"] for item in wd}  # 1..7(Sun..Sat)

    out_by_feed = []
    for feed_url, v in total_by_feed.items():
        out_by_feed.append({
            "feed_url": feed_url,
            "feed_title": v.get("title", feed_url),
            "total": v.get("total", 0),
            f"recent_{days}d": v.get("recent", 0),
        })

    # Calculate date range
    first_entry = entry_repo.find_one(sort=[("published", 1)])
    last_entry = entry_repo.find_one(sort=[("published", -1)])
    date_range = {
        "start_date": first_entry["published"].isoformat() if first_entry else None,
        "end_date": last_entry["published"].isoformat() if last_entry else None,
    }

    return {
        "generated_at": now,
        "days": days,
        "feeds": feed_repo.count(),
        "entries_total": total,
        "entries_recent": recent_cnt,
        "domains_top10": domains_out,
        "weekday_dist": weekday_dist,
        "by_feed": sorted(out_by_feed, key=lambda x: x["recent_7d" if days==7 else f"recent_{days}d"], reverse=True),
        "date_range": date_range,  # Add date range to output
    }
