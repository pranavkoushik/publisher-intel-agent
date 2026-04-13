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
    load_sent_urls,
    post_to_slack,
    quick_filter,
    save_sent_urls,
    soft_rank_and_limit,
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
    """Execute the full pipeline: fetch -> filter -> rank -> dedupe -> brief -> Slack."""
    label, publishers, coverage_label, _ = get_todays_publishers()

    if publishers is None:
        logger.info("Weekend — skipping run")
        return {"status": "skipped", "reason": "weekend"}

    logger.info("Running for %s (%d publishers)", label, len(publishers))

    # Fetch
    news = fetch_news(publishers, settings)
    logger.info("Fetched %d raw items", len(news))

    # Quick filter (remove old year URLs)
    news = quick_filter(news)
    logger.info("After quick filter: %d", len(news))

    # Rank and limit to top 15
    news = soft_rank_and_limit(news)

    # Date filter (HTML scraping + metadata)
    news = filter_recent_news(news, settings.news_lookback_days)
    logger.info("After date filter: %d", len(news))

    # Deduplicate by URL
    news = deduplicate_news(news)

    # Remove already-sent URLs (Google Sheets)
    sent_urls = load_sent_urls(settings)
    news = [item for item in news if item.get("url", "") not in sent_urls]
    logger.info("After Sheets dedup: %d unique new items", len(news))

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

    # Track sent URLs in Google Sheets
    save_sent_urls([item.get("url", "") for item in news], settings)

    return {
        "status": "success" if success else "slack_failed",
        "items": len(news),
        "coverage": coverage_label,
    }
