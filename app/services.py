"""Core service layer: Tavily search, Gemini analysis, Slack delivery."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

import google.generativeai as genai
import requests
from tavily import TavilyClient

from app.config import Settings

logger = logging.getLogger(__name__)


# ── Tavily News Fetching ─────────────────────────────────────────────────────

def fetch_news(publishers: list[str], settings: Settings) -> list[dict]:
    tavily = TavilyClient(api_key=settings.tavily_api_key)
    all_results: list[dict] = []

    search_limit = min(len(publishers), settings.publisher_search_limit)
    for pub in publishers[:search_limit]:
        query = (
            f"{pub} funding OR acquisition OR hiring OR layoffs "
            f"OR product launch OR pricing changes OR new location "
            f"OR new expansions last {settings.news_lookback_days} days"
        )
        try:
            results = tavily.search(
                query=query,
                search_depth=settings.tavily_search_depth,
                max_results=settings.tavily_max_results,
                days=settings.news_lookback_days,
            )
            all_results.extend(results.get("results", []))
            logger.info("Fetched %d results for %s", len(results.get("results", [])), pub)
        except Exception:
            logger.exception("Search failed for %s", pub)

    return all_results


def filter_recent_news(results: list[dict], lookback_days: int = 7) -> list[dict]:
    cutoff = datetime.now() - timedelta(days=lookback_days)
    filtered: list[dict] = []

    for item in results:
        pub_date_str = item.get("published_date")
        if pub_date_str:
            try:
                if datetime.fromisoformat(pub_date_str) >= cutoff:
                    filtered.append(item)
            except (ValueError, TypeError):
                filtered.append(item)
        else:
            filtered.append(item)

    return filtered


def deduplicate_news(results: list[dict]) -> list[dict]:
    seen_urls: set[str] = set()
    unique: list[dict] = []

    for item in results:
        url = item.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            unique.append(item)

    return unique


# ── Gemini Brief Generation ──────────────────────────────────────────────────

BRIEF_PROMPT_TEMPLATE = """\
You are the Joveo Publisher Intelligence Agent.

Today is {today}.

Below is REAL-TIME news data collected from the web:

{context}

TASK:
From this data, select the TOP 5 most impactful updates relevant to Joveo.

OUTPUT FORMAT:

📡 *Joveo Publisher Intel*
📅 {today}

━━━━━━━━━━━━━━━━━━

For each item:

[Impact Emoji] *[Publisher Name]*
[One sentence insight explaining what happened + why it matters to Joveo]

Source | 🔗 <URL>

(Repeat up to 5 items, each separated by a blank line)

━━━━━━━━━━━━━━━━━━

📊 _Coverage: {coverage_label}_
🔎 _Source: Tavily_

---

IMPACT TAG RULES:
- Use 🔥 for high-impact (funding, major product launches, large layoffs, acquisitions)
- Use ⚠️ for risk signals (declining hiring, layoffs, revenue pressure)
- Use 📈 for growth signals (expansion, hiring surge, new markets)
- Use 🧠 for strategic/product updates

---

FORMATTING RULES:
- Always include the URL as a clickable link using 🔗
- Keep each item visually separated
- Keep it clean and scannable
- Ensure there is a blank line between each item
- Do NOT cluster items together
- Keep formatting clean and readable

RULES:
- Only use the provided data. Order items by impact (highest first)
- No hallucination
- Max 5 items (Only important ones) - give less if 5 are not very important
- One sentence each

IMPORTANT:
- Focus on important news from the LAST 7 DAYS
"""


def generate_brief(
    news_data: list[dict],
    coverage_label: str,
    settings: Settings,
) -> str | None:
    genai.configure(api_key=settings.gemini_api_key)

    today = datetime.now().strftime("%A, %d %B %Y")
    context = "\n\n".join(
        f"TITLE: {item.get('title', 'N/A')}\n"
        f"URL: {item.get('url', 'N/A')}\n"
        f"CONTENT: {item.get('content', 'N/A')}"
        for item in news_data
    )

    prompt = BRIEF_PROMPT_TEMPLATE.format(
        today=today,
        context=context,
        coverage_label=coverage_label,
    )

    try:
        model = genai.GenerativeModel(settings.gemini_model)
        response = model.generate_content(prompt)
        return response.text.strip() if response.text else None
    except Exception:
        logger.exception("Gemini generation failed")
        return None


# ── Slack Delivery ───────────────────────────────────────────────────────────

def post_to_slack(message: str, settings: Settings) -> bool:
    for attempt in range(1, settings.slack_retries + 1):
        try:
            resp = requests.post(
                settings.slack_webhook_url,
                json={"text": message},
                timeout=settings.slack_timeout,
            )
            if resp.status_code == 200:
                logger.info("Slack message delivered (attempt %d)", attempt)
                return True
            logger.warning("Slack returned %d on attempt %d", resp.status_code, attempt)
        except Exception:
            logger.exception("Slack post attempt %d failed", attempt)

        if attempt < settings.slack_retries:
            time.sleep(2 ** attempt)

    logger.error("All %d Slack delivery attempts exhausted", settings.slack_retries)
    return False
