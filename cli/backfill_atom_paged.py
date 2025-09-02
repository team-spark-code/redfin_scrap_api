# cli/backfill_atom_paged.py (요약 버전)
import time, hashlib, requests, feedparser, os
from urllib.parse import urlparse
from datetime import datetime, timezone
from pymongo import MongoClient, UpdateOne

MONGO_URI = os.getenv("MONGO_URI")
DB = MongoClient(MONGO_URI)["redfin"]

def ek(feed_url, entry):
    eid = entry.get("id") or entry.get("link") or hashlib.sha256(
        f"{feed_url}|{entry.get('title')}|{entry.get('published_parsed')}".encode()
    ).hexdigest()
    return eid

def to_dt(e):
    for k in ("published_parsed","updated_parsed"):
        t = e.get(k)
        if t: return datetime(*t[:6], tzinfo=timezone.utc)
    return None

def mirror(feed_url, since_dt=None, limit_pages=50):
    url = feed_url; pages=0
    while url and pages < limit_pages:
        resp = requests.get(url, timeout=15); resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        ops=[]
        for e in parsed.entries:
            pub = to_dt(e)
            if since_dt and pub and pub < since_dt: return
            _id = ek(feed_url, e)
            dom = urlparse(e.get("link","")).netloc or None
            doc = {
              "_id": _id, "feed_url": feed_url,
              "title": e.get("title"), "link": e.get("link"),
              "published": pub, "updated": pub,
              "summary": e.get("summary"), "domain": dom,
              "mirrored_at": datetime.now(timezone.utc)
            }
            ops.append(UpdateOne({"_id":_id},{"$set":doc}, upsert=True))
        if ops: DB.entries.bulk_write(ops, ordered=False)
        # rel=next 탐색
        url=None
        for l in parsed.feed.get("links", []):
            if l.get("rel")=="next":
                url=l.get("href"); break
        pages += 1
        time.sleep(0.5)

# 사용 예: 올해 1/1 이후만
if __name__ == "__main__":
    since = datetime(2025,1,1, tzinfo=timezone.utc)
    mirror("https://some-atom-paged-feed.example/atom.xml", since_dt=since)
