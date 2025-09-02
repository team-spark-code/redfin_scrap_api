# app/agg_queries.py
from datetime import datetime, timedelta, timezone

def since_days(days: int):
    return datetime.now(timezone.utc) - timedelta(days=days)

def pipeline_recent_count(days: int):
    return [
        {"$match": {"published": {"$gte": since_days(days)}}},
        {"$count": "recent"}
    ]

def pipeline_domains_top(days: int, limit: int = 10):
    return [
        {"$match": {"published": {"$gte": since_days(days)}}},
        {"$group": {"_id": "$domain", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]

def pipeline_by_feed(days: int):
    return [
        {"$group": {"_id": "$feed_url", "total": {"$sum": 1}}},
        {"$lookup": {
            "from": "feeds",
            "localField": "_id",
            "foreignField": "_id",
            "as": "feed"
        }},
        {"$addFields": {"feed_title": {"$ifNull": [{"$arrayElemAt": ["$feed.title", 0]}, "$_id"]}}},
        {"$project": {"feed": 0}},
    ], [
        {"$match": {"published": {"$gte": since_days(days)}}},
        {"$group": {"_id": "$feed_url", "recent": {"$sum": 1}}},
    ]

def pipeline_weekday_dist():
    # 1=Sunday in $dayOfWeek; 0=Mon로 맞추려면 프론트에서 변환하거나 여기서 가공
    return [
        {"$match": {"published": {"$ne": None}}},
        {"$group": {"_id": {"$dayOfWeek": "$published"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
