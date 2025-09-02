from __future__ import annotations
from dotenv import load_dotenv ; load_dotenv()
import hashlib
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from inspect import signature
import requests
from bs4 import BeautifulSoup
from feedsearch import search as fs_search
from pymongo import MongoClient, UpdateOne
from reader import make_reader

from .config import RSS_DB_PATH, MONGO_URI, MONGO_DB, AI_FEEDS, BLACKLIST_FEEDS, BLACKLIST_DOMAINS
from .agg_queries import pipeline_recent_count, pipeline_domains_top, pipeline_by_feed, pipeline_weekday_dist

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

# ---------- Mongo ----------
def _mdb():
    cli = MongoClient(MONGO_URI)
    db = cli[MONGO_DB]
    db.entries.create_index([("feed_url", 1), ("published", -1)])
    db.entries.create_index([("domain", 1), ("published", -1)])
    db.entries.create_index([("published", -1)])
    return db

# ---------- Init & Update ----------
def init_feeds() -> Dict[str, Any]:
    r = _reader()
    added, skipped = 0, 0
    for url in AI_FEEDS:
        try:
            r.add_feed(url)
            added += 1
        except Exception:
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

def update_all(days: Optional[int] = 1) -> Dict[str, Any]:
    r = _reader()
    start = time.time()
    r.update_feeds()
    me = mirror_entries_to_mongo(days=days)  # 증분 미러(기본 1일)
    return {"updated": True, "update_sec": round(time.time() - start, 2), "mongo_entries": me}

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
    from pymongo import UpdateOne
    db = _mdb()
    r = _reader()
    ops = []
    for f in r.get_feeds():
        url = getattr(f, "url", None)
        title = getattr(f, "title", None) or url
        site_url = getattr(f, "link", None) or url
        if not url: continue
        ops.append(UpdateOne({"_id": url}, {"$set": {
            "title": title,
            "site_url": site_url,
        }}, upsert=True))
    if ops:
        res = db.feeds.bulk_write(ops, ordered=False)
        return {"feeds_upserted": res.upserted_count, "feeds_modified": res.modified_count}
    return {"feeds_upserted": 0, "feeds_modified": 0}

def mirror_entries_to_mongo(days: Optional[int] = None) -> Dict[str, Any]:
    r = _reader()
    db = _mdb()

    # 기간 기준 계산
    newer_ts = None
    if days:
        newer_ts = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()

    # reader 버전에 따라 분기
    if newer_ts is not None and _supports_newer_than(r):
        it = r.get_entries(newer_than=newer_ts)  # 신버전 경로
    else:
        it = r.get_entries()  # 구버전 경로(수동 필터)

    ops, cnt = [], 0
    for e in it:
        # 구버전 경로일 때 수동 필터
        if newer_ts is not None and not _supports_newer_than(r):
            pub_ts = _to_ts(getattr(e, "published", None)) or _to_ts(getattr(e, "updated", None))
            if pub_ts is None or pub_ts < newer_ts:
                continue

        cnt += 1
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
        ops.append(UpdateOne({"_id": _id}, {"$set": doc}, upsert=True))
        if len(ops) >= 1000:
            db.entries.bulk_write(ops, ordered=False); ops.clear()

    if ops:
        db.entries.bulk_write(ops, ordered=False)
    return {"entries_processed": cnt}

# ---------- Stats (Mongo Aggregation) ----------
def stats(days: int = 7) -> Dict[str, Any]:
    db = _mdb()
    now = datetime.now(timezone.utc).isoformat()

    total = db.entries.estimated_document_count()
    recent = list(db.entries.aggregate(pipeline_recent_count(days)))
    recent_cnt = recent[0]["recent"] if recent else 0

    domains = list(db.entries.aggregate(pipeline_domains_top(days, 10)))
    domains_out = [{"domain": d["_id"] or "(none)", "count": d["count"]} for d in domains]

    pipe_total, pipe_recent = pipeline_by_feed(days)
    total_by_feed = {d["_id"]: {"total": d["total"], "title": d.get("feed_title", d["_id"])}
                     for d in db.entries.aggregate(pipe_total)}
    for d in db.entries.aggregate(pipe_recent):
        total_by_feed.setdefault(d["_id"], {"total": 0, "title": d["_id"]})
        total_by_feed[d["_id"]]["recent"] = d["recent"]

    # 요일 분포
    wd = list(db.entries.aggregate(pipeline_weekday_dist()))
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
    first_entry = db.entries.find_one(sort=[("published", 1)])
    last_entry = db.entries.find_one(sort=[("published", -1)])
    date_range = {
        "start_date": first_entry["published"].isoformat() if first_entry else None,
        "end_date": last_entry["published"].isoformat() if last_entry else None,
    }

    return {
        "generated_at": now,
        "days": days,
        "feeds": db.feeds.estimated_document_count(),
        "entries_total": total,
        "entries_recent": recent_cnt,
        "domains_top10": domains_out,
        "weekday_dist": weekday_dist,
        "by_feed": sorted(out_by_feed, key=lambda x: x["recent_7d" if days==7 else f"recent_{days}d"], reverse=True),
        "date_range": date_range,  # Add date range to output
    }
