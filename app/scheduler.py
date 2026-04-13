"""Weekday-based publisher scheduling and the daily job runner."""

from __future__ import annotations

import datetime
import logging

from app.config import Settings
from app.publishers import P0_PUBLISHERS, P1_P2_BATCHES
from app.services import (
    deduplicate_news,
    fetch_news,
    filter_recent_news,
    generate_brief,
    post_to_slack,
)

logger = logging.getLogger(__name__)

ScheduleEntry = tuple[str, list[str], str, str] | tuple[None, None, None, None]


def get_todays_publishers() -> ScheduleEntry:
    """Return (label, publishers, coverage_label, next_label) based on weekday."""
    today = datetime.date.today()
    weekday = today.weekday()
    week_num = today.isocalendar()[1]

    schedule: dict[int, tuple[str, list[str], str, str]] = {
        0: ("P0", P0_PUBLISHERS, "P0 publishers", "P1/P2 Batch 1 Tuesday"),
        1: ("P1/P2 Batch 1", P1_P2_BATCHES[week_num % 3], "P1/P2 Batch 1", "P1/P2 Batch 2 Wednesday"),
        2: ("P1/P2 Batch 2", P1_P2_BATCHES[(week_num + 1) % 3], "P1/P2 Batch 2", "P1/P2 Batch 3 Friday"),
        3: ("P0", P0_PUBLISHERS, "P0 publishers", "P1/P2 Batch 3 Friday"),
        4: ("P1/P2 Batch 3", P1_P2_BATCHES[(week_num + 2) % 3], "P1/P2 Batch 3", "P0 publishers Monday"),
    }

    if weekday not in schedule:
        return None, None, None, None

    return schedule[weekday]


def run_daily_job(settings: Settings) -> dict:
    """Execute the full pipeline: fetch -> filter -> brief -> Slack."""
    label, publishers, coverage_label, _ = get_todays_publishers()

    if publishers is None:
        logger.info("Weekend — skipping run")
        return {"status": "skipped", "reason": "weekend"}

    logger.info("Running for %s (%d publishers)", label, len(publishers))

    news = fetch_news(publishers, settings)
    news = filter_recent_news(news, settings.news_lookback_days)
    news = deduplicate_news(news)
    logger.info("Collected %d unique news items after filtering", len(news))

    if not news:
        today_str = datetime.date.today().strftime("%A, %d %B %Y")
        fallback = (
            f"📡 Joveo Publisher Intel — {today_str}\n\n"
            f"No impactful updates relevant to Joveo were found for "
            f"{coverage_label} within the last 7 days.\n\n"
            f"Researched via: Tavily\nCoverage today: {coverage_label}"
        )
        post_to_slack(fallback, settings)
        return {"status": "no_news", "coverage": coverage_label}

    logger.info("Generating Gemini brief…")
    brief = generate_brief(news, coverage_label, settings)

    if not brief:
        logger.error("Brief generation failed — skipping Slack")
        return {"status": "error", "reason": "brief_generation_failed"}

    success = post_to_slack(brief, settings)
    return {
        "status": "success" if success else "slack_failed",
        "items": len(news),
        "coverage": coverage_label,
    }
