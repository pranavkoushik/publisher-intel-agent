"""FastAPI application — Publisher Intelligence Agent."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.scheduler import get_todays_publishers, run_daily_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()

    missing = []
    if not settings.slack_webhook_url:
        missing.append("SLACK_WEBHOOK_URL")
    if not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not settings.tavily_api_key:
        missing.append("TAVILY_API_KEY")

    if missing:
        logger.warning("Missing env vars: %s — scheduler disabled, set them in your hosting dashboard", ", ".join(missing))
    else:
        scheduler.add_job(
            run_daily_job,
            CronTrigger(
                day_of_week="mon-fri",
                hour=settings.cron_hour,
                minute=settings.cron_minute,
            ),
            args=[settings],
            id="daily_publisher_intel",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            "Scheduler started — job runs Mon-Fri at %02d:%02d",
            settings.cron_hour,
            settings.cron_minute,
        )

    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")


app = FastAPI(
    title="Joveo Publisher Intelligence Agent",
    version="1.0.0",
    description="Automated publisher news monitoring with Slack delivery",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schedule")
def schedule_info():
    """Show today's publisher schedule."""
    label, publishers, coverage, next_label = get_todays_publishers()
    if publishers is None:
        return {"today": "weekend", "publishers": [], "next": None}
    return {
        "today": label,
        "publisher_count": len(publishers),
        "publishers": publishers,
        "coverage": coverage,
        "next": next_label,
    }


@app.post("/run-job")
def trigger_job(settings: Settings = Depends(get_settings)):
    """Manually trigger the daily intelligence job."""
    if not all([settings.slack_webhook_url, settings.gemini_api_key, settings.tavily_api_key]):
        raise HTTPException(status_code=503, detail="Missing required API keys. Set SLACK_WEBHOOK_URL, GEMINI_API_KEY, TAVILY_API_KEY.")
    result = run_daily_job(settings)
    return result
