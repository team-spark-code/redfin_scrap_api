# backend/core/config.py
from dotenv import load_dotenv
load_dotenv()
import os
from pathlib import Path

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# FastAPI 설정
PROJECT_NAME = "RedFin RSS"
VERSION = "0.1.0"
API_V1_PREFIX = "/api/v1"

# Reader용 SQLite (캐시/중복제어용) — 실행 위치와 무관하게 고정
RSS_DB_PATH = os.getenv("RSS_DB_PATH", str(DATA_DIR / "rss.sqlite"))

# Mongo
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:Redfin7620%21@localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "redfin")
MONGO_COL = os.getenv("MONGO_COL", "rss_feeds")

# CORS 설정
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
]

# 발견(Discover) 기본 타깃 URL들
# 섹션/태그/카테고리 URL을 늘리면 feedsearch + HTML <link>로 RSS 후보를 찾아 자동 등록
DISCOVER_TARGETS = [
    "https://techcrunch.com/tag/artificial-intelligence/",
    "https://venturebeat.com/category/ai/",
    "https://www.theverge.com/ai-artificial-intelligence",
    "https://medium.com/tag/machine-learning",
    "https://ai.googleblog.com/",
]

# 초기 AI 피드 (마이그레이션용 - MongoDB로 이전됨)
# 주의: 이 리스트는 마이그레이션(/feeds/migrate API)에만 사용됩니다.
# 새로운 피드는 MongoDB에 직접 추가하거나 /feeds API를 사용하세요.
AI_FEEDS = [
    # --- Frontier / Big Tech Labs ---
    "https://openai.com/blog/rss.xml",
    "https://ai.googleblog.com/atom.xml",
    "https://www.deepmind.com/blog.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://developer.nvidia.com/blog/feed",
    "https://nvidianews.nvidia.com/rss",
    "https://engineering.fb.com/feed/",
    "https://www.microsoft.com/en-us/research/blog/feed/",
    "https://blog.google/technology/ai/rss/",
    # --- Korea Frontier Labs ---
    "https://medium.com/kakao-ai/feed",
    "https://news.samsung.com/global/category/technology/artificial-intelligence/feed",
    # --- Academia / Research Labs ---
    "https://bair.berkeley.edu/blog/feed.xml",
    "https://blog.ml.cmu.edu/feed/",
    "http://ai.stanford.edu/blog/feed.xml",
    "https://blog.eleuther.ai/index.xml",
    "https://www.alignmentforum.org/rss",
    # --- Korea Academia ---
    "https://medium.com/snu-aiis-blog/feed",
    # --- Cloud AI ---
    "https://aws.amazon.com/blogs/machine-learning/feed/",
    "https://blog.google/feed/",
    # --- Research Paper Streams (arXiv) ---
    "https://export.arxiv.org/rss/cs.AI",
    "https://export.arxiv.org/rss/cs.LG",
    "https://export.arxiv.org/rss/cs.CL",
    "https://export.arxiv.org/rss/stat.ML",
    # --- Media / Aggregators ---
    "https://thegradient.pub/rss/",
    "https://www.marktechpost.com/feed",
    "https://the-decoder.com/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed",
    "https://towardsdatascience.com/feed",
    "https://thenewstack.io/category/artificial-intelligence/feed/",
    "https://hnrss.org/frontpage?points=200&count=50&secondary=false&tag=ai",
]

# 임시로 넣고 백필 후 제거해도 됨
AI_FEEDS += [
    "https://thenewstack.io/2025/01/feed/",
    "https://thenewstack.io/2025/02/feed/",
]

BLACKLIST_FEEDS = {
    # 정확한 피드 URL
    "https://example.com/broken/feed.xml",
}

BLACKLIST_DOMAINS = {
    # 도메인 단위 차단
    "spam.example.com",
}

