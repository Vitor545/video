import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.presentation import auth, courses, dashboard, downloads, management, videos
from app.application.downloads import download_worker, rehydrate_jobs
from app.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — rehydrating download jobs...")
    try:
        await rehydrate_jobs(AsyncSessionLocal)
    except Exception as e:
        logger.error("rehydrate_jobs failed: %s", e)
    worker_task = asyncio.create_task(download_worker(AsyncSessionLocal))
    logger.info("Download worker task created.")
    yield
    worker_task.cancel()

app = FastAPI(title="DevOps Platform", version="0.1.0", docs_url="/docs", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(downloads.router)
app.include_router(management.router)
app.include_router(videos.router)
app.include_router(dashboard.router)

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/ready", tags=["system"])
async def ready(response: Response):
    checks: dict[str, str] = {}
    ok = True
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
        ok = False
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if ok else "degraded", "checks": checks}
