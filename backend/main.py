# backend/main.py
"""FastAPI 애플리케이션 진입점"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import PROJECT_NAME, VERSION, API_V1_PREFIX, CORS_ORIGINS
from backend.api.v1.api import api_router

app = FastAPI(
    title=PROJECT_NAME,
    description="AI RSS News API Scrap Service",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(api_router, prefix=API_V1_PREFIX)

# 루트 경로 (레거시 호환성)
@app.get("/")
def root():
    return {"message": "RedFin RSS API", "version": VERSION, "docs": "/docs"}

# 레거시 경로 호환성 (기존 API 경로 유지)
@app.get("/health")
def health():
    return {"ok": True}

@app.post("/init")
def init():
    from backend.core.container import Container
    service = Container.get_crawler_service()
    return service.init_feeds()

@app.post("/update")
async def update(days: int = 1):
    from fastapi import BackgroundTasks, status
    from backend.core.container import Container
    background_tasks = BackgroundTasks()
    service = Container.get_crawler_service()
    days_param = None if days == 0 else days
    background_tasks.add_task(service.update_all, days=days_param)
    return {
        "status": "accepted",
        "message": f"피드 업데이트가 백그라운드에서 시작되었습니다 (days={days_param or 'all'})",
        "days": days_param
    }

@app.get("/stats")
def get_stats(days: int = 7):
    from backend.core.container import Container
    service = Container.get_crawler_service()
    return service.get_stats(days=days)

@app.post("/discover")
def discover(url: str, top_k: int = 3):
    from backend.core.container import Container
    service = Container.get_feed_service()
    return service.discover_feeds(url, top_k=top_k)

@app.get("/feeds")
def list_feeds(enabled: bool | None = None):
    from backend.core.container import Container
    service = Container.get_feed_service()
    feeds = service.get_all_feeds(enabled=enabled)
    return {"feeds": feeds, "total": len(feeds)}

@app.post("/feeds")
def add_feed(url: str, title: str | None = None, enabled: bool = True):
    from fastapi import Body
    from backend.core.container import Container
    service = Container.get_feed_service()
    return service.add_feed(url, title=title, enabled=enabled)

@app.delete("/feeds/{url:path}")
def remove_feed(url: str):
    from backend.core.container import Container
    service = Container.get_feed_service()
    return service.remove_feed(url)

@app.patch("/feeds/{url:path}")
def update_feed_enabled(url: str, enabled: bool = True):
    from fastapi import Body
    from backend.core.container import Container
    service = Container.get_feed_service()
    return service.update_feed_enabled(url, enabled)

@app.post("/feeds/migrate")
def migrate_feeds():
    from backend.core.container import Container
    service = Container.get_feed_service()
    return service.migrate_feeds_from_config()

