# MongoDB 전략

일간, 주간, 월간 피드를 시간 범위별로 추출(필터링, 쿼리, 집계 등)하여 트렌드 리포트 발행을
위한 기사 데이터 확보

1. 인덱스 전략
    - 필터(특정 feed_url/domain) + 최신순 페이징, 기간 필터에 최적.
        ```js
        db.entries.createIndex({ published: -1 })
        db.entries.createIndex({ feed_url: 1, published: -1 })
        db.entries.createIndex({ domain: 1, published: -1 })
        ```

2. 기간 필터(일/주/월) 기본 패턴
    - 서울 타임존 기준 경계 사용
    - 보통은 서버에서 시작/종료 시각을 계산해서 $match에 넘기는 게 명확
        ```js
        // 일간: 어제 00:00~오늘 00:00
        const tz = "Asia/Seoul";
        const today = new Date(); // UTC now
        db.entries.aggregate([
        { $match: { published: { $gte: { $dateTrunc: { date: today, unit: "day", timezone: tz } } ,
                                $lt:  { $dateTrunc: { date: today, unit: "day", timezone: tz } } } } } 
                                // 예시는 오늘; 실전은 어제/임의일
        ])
        ```

3. $dateTrunc로 버킷(일/주/월)
    - 일간 Top N 기사(최근 7일, 도메인 기준 집계 예시)
        ```js
        const tz = "Asia/Seoul";
        db.entries.aggregate([
        { $match: { published: { $gte: new Date(Date.now() - 7*24*3600*1000) } } },
        { $addFields: {
            day: { $dateTrunc: { date: "$published", unit: "day", timezone: tz } }
        }},
        { $group: {
            _id: { day: "$day", domain: "$domain" },
            count: { $sum: 1 },
            sample: { $first: { title: "$title", link: "$link" } }
        }},
        { $sort: { "_id.day": -1, count: -1 } },
        { $group: {
            _id: "$_id.day",
            top: { $push: { domain: "$_id.domain", count: "$count", sample: "$sample" } }
        }},
        { $project: { day: "$_id", top: { $slice: ["$top", 10] }, _id: 0 } },
        { $sort: { day: -1 } }
        ])
        ```

    - 주간/월간 버전
        ```js
        // 주간(월요일 시작): unit: "week" + timezone
        { $addFields: { week: { $dateTrunc: { date: "$published", unit: "week", timezone: "Asia/Seoul" } } } }

        // 월간:
        { $addFields: { month: { $dateTrunc: { date: "$published", unit: "month", timezone: "Asia/Seoul" } } } }
        ```

4. 기간별 “원본 문서 리스트” 조회(요약 입력용)
    - 예: 주간 범위의 문서 목록(선택 필드만) + 페이징:
    - 아래 코드 실행 결과를 그대로 AI 요약 입력 배치로 사용
    - feed_url 또는 domain 필터를 추가하여 피드별/도메인별 요약도 동일 패턴
        ```js
        const weekStart = new Date("2025-08-25T15:00:00Z"); // 2025-08-26 00:00 KST
        const weekEnd   = new Date("2025-09-01T15:00:00Z"); // 2025-09-02 00:00 KST

        db.entries.find(
        { published: { $gte: weekStart, $lt: weekEnd }, domain: { $nin: [null, ""] } },
        { projection: { _id: 1, title: 1, link: 1, summary: 1, feed_url: 1, domain: 1, published: 1 } }
        ).sort({ published: -1 }).limit(500)
        ```

5. 단일 파이프라인으로 “집계 + 리스트” 동시 추출 ($facet)
    - 응답에서 list를 요약용 입력, domains/feeds는 KPI에 사용
        ```js
        const start = new Date("2025-09-01T00:00:00Z");
        const end   = new Date("2025-09-02T00:00:00Z");

        db.entries.aggregate([
        { $match: { published: { $gte: start, $lt: end } } },
        { $facet: {
            list: [
                { $sort: { published: -1 } },
                { $project: { _id: 1, title: 1, link: 1, summary: 1, feed_url: 1, domain: 1, published: 1 } },
                { $limit: 500 }
            ],
            domains: [
                { $group: { _id: "$domain", count: { $sum: 1 } } },
                { $sort: { count: -1 } }, { $limit: 10 }
            ],
            feeds: [
                { $group: { _id: "$feed_url", count: { $sum: 1 } } },
                { $sort: { count: -1 } }, { $limit: 20 }
            ]
        }}
        ])
        ```

6. 요약 파이프라인(권장 워크플로우)
    - 컬렉션 설계
        ```js
        db.summaries.createIndex({ scope: 1, period_start: 1, period_unit: 1 }, { unique: true })
        // 예: scope = {type: "global"} or {type: "feed", feed_url: "..."} or {type: "domain", domain: "..."}
        ```

    - 문서 예시
        ```json
        {
        "scope": { "type": "global" },               // or {"type":"feed","feed_url":...}
        "period_unit": "day|week|month",
        "period_start": ISODate("2025-09-01T00:00:00Z"),
        "period_end": ISODate("2025-09-02T00:00:00Z"),
        "stats": { "count": 212, "top_domains": [...], "top_feeds": [...] }, // 선택
        "summary_text": "…",            // LLM 결과
        "highlights": [ {title, link}, ... ],         // LLM가 뽑은 Top N
        "created_at": ISODate("…"), "updated_at": ISODate("…")
        }
        ```

    - 생성 절차
        1. Airflow 또는 FastAPI 백엔드에서 기간 계산(일/주/월).
        2. `entries`에서 해당 기간 + 선택 스코프(feed/domain/global)로 문서 find 또는 aggregate
        3. 텍스트 필드(`title + summary` 등)로 프롬프트 구성 → LLM 요약
        4. `summaries`에 upsert
            ```python
            # Python(pymongo)
            db.summaries.update_one(
            {"scope": scope, "period_unit": unit, "period_start": start_dt},
            {"$set": {
                "period_end": end_dt,
                "stats": stats_doc,
                "summary_text": llm_text,
                "highlights": highlights,
                "updated_at": datetime.utcnow()
            }, "$setOnInsert": { "created_at": datetime.utcnow() }},
            upsert=True
            )
            ```
        5. Next.js는 `/summaries?unit=week&start=...&scope=global` 같은 API로 조회만

    7. FastAPI 엔드포인트(요약 트리거/조회)
        ```python
        # /summarize?unit=day&start=2025-09-01&scope=global
        # 1) 기간→쿼리→문서 리스트 수집  2) LLM 호출  3) summaries upsert
        # 4) GET /summaries?unit=day&start=... (조회 전용)
        ```

    8. 다중 스코프 지원 패턴
        - global: 전체 entries
        - feed별: feed_url로 필터 → 각 feed에 대해 반복
        - domain별: domain으로 필터 → 상위 TopK만 요약
        - 카테고리/태그: 이후 메타데이터가 생기면 동일 패턴

    9. 성능 팁
        - 요약 입력은 길이 제한(예: 500~1000건, 또는 토큰 수 기준) → 초과분은 “제목/키포인트만” 사용.
        - 초벌 집계($group, $count 등) 결과를 프롬프트 보조로 사용(주요 트렌드/Top domain/Top feed).
        - 필요 시 precompute 테이블(daily_entries, weekly_entries)에 사전 집계 결과를 저장하고, 요약은 그 결과만 사용.

    10. 샘플 Python 함수(주간 글로벌 요약 입력 추출)
        - 반환 리스트를 LLM에 넣고, 결과는 `summaries`에 upsert
        ```python
        from datetime import datetime, timedelta, timezone
        from pymongo import MongoClient

        def weekly_window_utc(ks_monday_dt):  # ks_monday_dt: KST의 월요일 00:00
            start_utc = ks_monday_dt.astimezone(timezone.utc)
            end_utc = (ks_monday_dt + timedelta(days=7)).astimezone(timezone.utc)
            return start_utc, end_utc

        def fetch_week_docs(mongo_uri, dbname, start_utc, end_utc, limit=500):
            cli = MongoClient(mongo_uri); db = cli[dbname]
            cur = db.entries.find(
                {"published": {"$gte": start_utc, "$lt": end_utc}},
                {"title":1,"link":1,"summary":1,"feed_url":1,"domain":1,"published":1}
            ).sort("published", -1).limit(limit)
            return list(cur)
        ```

### 결론
- MongoDB의 $dateTrunc + 기간 필터 + 인덱스로 일/주/월 추출을 안정적으로 처리합니다.
- 요약 결과는 summaries 컬렉션에 스코프/기간 단위로 upsert하여 재요약 방지와 조회 성능을 확보합니다.
- Airflow는 스케줄링과 리트라이, FastAPI는 요약 트리거/조회 API를 담당하게 분리하면 운영이 깔끔합니다.