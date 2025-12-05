# Redfin Scraper v2

### 프로젝트 구조
```bash
redfin_rss/
├─ app/
│  ├─ __init__.py
│  ├─ config.py                  # 경로/환경변수, Mongo/DB 설정
│  ├─ rss_core.py                # 공용 로직(수집, 발견, Mongo 미러링, 통계)
│  ├─ agg_queries.py             # Mongo Aggregation 파이프라인 모음
│  └─ repositories/              # Repository Pattern (데이터 접근 계층)
│     ├─ __init__.py
│     ├─ database.py             # MongoDB 연결 관리 (싱글톤)
│     ├─ base.py                 # BaseRepository 추상 클래스
│     ├─ feed_repository.py      # FeedRepository 구현
│     └─ entry_repository.py     # EntryRepository 구현
├─ api/
│  └─ main.py                    # FastAPI: /health /init /update /discover /stats /feeds
├─ cli/
│  ├─ rss_tool.py                # 단일 실행 CLI (update/stats/discover/opml-export)
│  └─ init_indexes.py            # MongoDB 인덱스 초기화 스크립트
├─ dags/
│  └─ rss_pipeline.py            # Airflow DAG (HTTP로 FastAPI 호출 or 직접 import)
├─ frontend/                     # Next.js (원페이지 관리자 UI)
│  ├─ app/
│  │  └─ page.tsx
│  ├─ components/
│  │  ├─ kpi-cards.tsx
│  │  └─ top-table.tsx
│  ├─ package.json
│  ├─ next.config.mjs
│  └─ .env.local.example
├─ data/                         # DB/산출물 보관 (gitignore)
├─ .env.example
├─ requirements.txt
└─ .gitignore
```


### 설치
```bash
## 1. FastAPI 설치
# 가상 환경 설치
uv python list
uv python install 3.10.18
uv venv --python 3.10.18 .scrap
source .scrap/bin/activate

# 의존성 설치
uv pip install fastapi uvicorn "werkzeug<3.0.0" reader feedparser feedsearch beautifulsoup4 lxml charset-normalizer dotenv pymongo pyyaml python-multipart
# sqlite3 저장을 위한 data/ 생성 및 권한 부여
mkdir -p data
chmod -R u+rwX data


## 2. Next.js 설치
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
source ~/.bashrc

nvm install 22.18.0
nvm use 22.18.0
nvm alias default 22.18.0

corepack enable
corepack prepare pnpm@latest --activate

pnpm --version

# 초기 실행 (1번)
pnpm create next-app@14.2.31 redfin_scraper_ui \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --strict

cd ~/workspace/redfin_scraper_ui
pnpm install
pnpm dev
```

### 실행
```bash
# FastAPI
uvicorn api.main:app --host 0.0.0.0 --port 8030 --reload
uvicorn api.main:app --host 0.0.0.0 --port 8030 --reload --log-level debug
PYTHONPATH=$(pwd) uvicorn api.main:app --host 0.0.0.0 --port 8030 --reload

# CLI 단일 실행
python cli/rss_tool.py init-indexes  # MongoDB 인덱스 초기화 (최초 1회만 실행)
python cli/rss_tool.py init   # 초기 셋업 + 첫 업데이트
python cli/rss_tool.py update # 주기 수집
python cli/rss_tool.py stats --days 7 --out data/stats-7d.json # 통계 (최근 7일)
python rss_tool.py discover --url https://techcrunch.com/tag/artificial-intelligence/ --top-k 3 # 신규 

# 피드 탐색 및 추가
python rss_tool.py opml-export --out feeds.opml # 현재 구독 내보내기(OPML)

# (선택) feeds.yaml → Reader 등록/정합화
python -m cli.feeds_sync --sync-yaml

# 필요 시 Reader에만 있는 피드 제거도 수행
python -m cli.feeds_sync --sync-yaml --delete-missing

# (선택) OPML 대량 import (블랙리스트 자동 제외)
python -m cli.feeds_sync --import-opml data/my_feeds.opml

# (선택) 현재 Reader → OPML로 백업
python -m cli.feeds_sync --export-opml

# 전체 백필 (한 번만)
curl -X POST "http://localhost:8030/update?days=0"

# ------------------------------------------------------------------------------
# Next.js
cd frontend && cp .env.local.example .env.local && npm i && npm run dev
# → http://localhost:3000 접속


# Airflow (HTTP Operator)
# Airflow UI에서 conn_id="rss_api"로 http://host.docker.internal:8030 등 등록 후 DAG on
```

### 초기화 & 활용
```bash
# MongoDB 인덱스 초기화 (최초 1회만 실행, 앱 시작 전 권장)
python cli/rss_tool.py init-indexes
# 또는
python -m cli.init_indexes

# 헬스체크
curl http://localhost:8030/health
#{"ok":true}

# 초기화 (MongoDB에서 활성화된 피드를 Reader에 등록)
curl -X POST http://localhost:8030/init
#{"added":25,"skipped":0,"update_sec":5.14,"mongo_entries":{"entries_processed":150},"mongo_feeds":{"feeds_upserted":25,"feeds_modified":0}}

# 피드 업데이트 (비동기, 즉시 202 Accepted 응답)
curl -X POST http://localhost:8030/update
# {"status":"accepted","message":"피드 업데이트가 백그라운드에서 시작되었습니다 (days=1)","days":1}

# 통계 조회
curl "http://localhost:8030/stats?days=7"
#{"generated_at":"2025-09-02T12:45:36.667341+00:00","days":7,"feeds":25,"entries_total":1342,"entries_recent":212,"domains_top10":[{"domain":"huggingface.co","count":45}],"weekday_dist":{"1":30,"2":34,"3":33},"by_feed":[{"feed_url":"https://huggingface.co/blog/feed.xml","feed_title":"Hugging Face Blog","total":150,"recent_7d":45}]}
```

### 피드 관리 (코드 배포 없이 피드 추가/삭제/활성화)
```bash
# 기존 config.py의 AI_FEEDS를 MongoDB로 마이그레이션 (최초 1회)
curl -X POST http://localhost:8030/feeds/migrate
#{"migrated":25,"skipped":0,"total":25}

# 피드 목록 조회
curl "http://localhost:8030/feeds"
# 활성화된 피드만 조회
curl "http://localhost:8030/feeds?enabled=true"

# 피드 추가
curl -X POST "http://localhost:8030/feeds" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/feed.xml", "title": "Example Feed", "enabled": true}'

# 피드 비활성화
curl -X PATCH "http://localhost:8030/feeds/https://example.com/feed.xml" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# 피드 삭제
curl -X DELETE "http://localhost:8030/feeds/https://example.com/feed.xml"
```

### 주요 변경사항
- **Repository Pattern**: 데이터 접근 계층 분리, PyMongo 직접 사용 제거
- **비동기 수집**: `/update` API가 백그라운드에서 실행되어 즉시 응답 반환
- **피드 설정 DB화**: MongoDB에서 피드 관리, 코드 배포 없이 피드 추가/삭제 가능
- **인덱스 최적화**: 별도 초기화 스크립트로 분리, 앱 시작 속도 개선

### 운영 팁
- **인덱스 초기화**: 최초 1회 `python cli/rss_tool.py init-indexes` 실행 (앱 시작 전 권장)
- **피드 마이그레이션**: 기존 config.py의 AI_FEEDS를 MongoDB로 이전 (`/feeds/migrate` API)
- **백필**: `/backfill?days=365` 등으로 Mongo에 최소 6–12개월치 적재 → 대시보드 유의미
- **비동기 업데이트**: `/update` API는 즉시 응답 반환, 백그라운드에서 수집 수행 (로그 확인)
- **피드 관리**: 코드 배포 없이 `/feeds` API로 피드 추가/삭제/활성화 가능
- **Discover 주기화**: Airflow에서 주 1회 도메인 리스트 순회 → 신규 RSS 자동추가
- **휴면 피드 청소**: 30일 이상 신규 없음 → `/feeds` API로 비활성화 또는 삭제
- **에러 로깅**: 업데이트 시 피드별 HTTP/파싱 에러 카운트 집계 → 장애 피드 감지


### Next.js 입력 대시보드
- 총 피드/최근 N일 기사 수(카드)
- 도메인 Top 10 (막대)
- 요일 분포 (막대/히트맵)
- 피드별 전체/최근 (테이블 + 정렬/필터)
- 평균 제목 길이/발행시각 누락/평균 publish age(요약 KPI)

```json
{
  "generated_at": "2025-09-02T09:00:00.000Z",
  "days": 7,
  "feeds": 12,
  "entries_total": 1342,
  "entries_recent": 212,
  "title_length": { "avg": 56.38, "median": 54 },
  "missing_published": 3,
  "avg_publish_age_hours": 18.42,
  "domains_top10": [
    {"domain": "openai.com", "count": 120},
    {"domain": "ai.googleblog.com", "count": 98}
  ],
  "weekday_dist": { "0": 30, "1": 34, "2": 33, "3": 28, "4": 40, "5": 22, "6": 25 },
  "by_feed": [
    { "feed_url": "https://openai.com/blog/rss", "feed_title": "OpenAI Blog", "total": 400, "recent_7d": 40 }
  ]
}
```
- 
