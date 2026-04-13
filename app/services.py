"""Core service layer: Tavily search, Gemini analysis, Slack delivery, Google Sheets tracking."""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import google.generativeai as genai
import gspread
import requests
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
from tavily import TavilyClient

from app.config import Settings

logger = logging.getLogger(__name__)

SHEET_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


# ── Google Sheets ────────────────────────────────────────────────────────────

def _get_sheet(settings: Settings):
    creds_file = settings.google_credentials_file
    creds_json = settings.google_credentials_json

    if creds_file:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, SHEET_SCOPES)
    elif creds_json:
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SHEET_SCOPES)
    else:
        logger.warning("No Google credentials configured — Sheets tracking disabled")
        return None

    client = gspread.authorize(creds)
    return client.open(settings.google_sheet_name).sheet1


def load_sent_urls(settings: Settings) -> set[str]:
    try:
        sheet = _get_sheet(settings)
        if sheet is None:
            return set()
        return set(sheet.col_values(1))
    except Exception:
        logger.exception("Failed to load sent URLs from Sheets")
        return set()


def save_sent_urls(urls: list[str], settings: Settings) -> None:
    try:
        sheet = _get_sheet(settings)
        if sheet is None:
            return
        existing = set(sheet.col_values(1))
        new_urls = [url for url in urls if url not in existing]
        if new_urls:
            sheet.append_rows([[url] for url in new_urls])
            logger.info("Saved %d new URLs to Sheets", len(new_urls))
    except Exception:
        logger.exception("Failed to save sent URLs to Sheets")


# ── Tavily News Fetching ─────────────────────────────────────────────────────

def fetch_news(publishers: list[str], settings: Settings) -> list[dict]:
    tavily = TavilyClient(api_key=settings.tavily_api_key)
    all_results: list[dict] = []

    search_limit = min(len(publishers), settings.publisher_search_limit)
    for pub in publishers[:search_limit]:
        query = (
            f'("{pub}") AND (funding OR acquisition OR hiring OR layoffs '
            f"OR product launch OR expansion OR launch OR feature OR product "
            f"OR update OR new OR ai OR platform OR tool OR partnership "
            f"OR integration OR growth OR strategy) AND (last 7 days)"
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


# ── Date Extraction ──────────────────────────────────────────────────────────

def fetch_article_date(url: str) -> datetime | None:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")

        meta_tags = [
            {"property": "article:published_time"},
            {"name": "article:published_time"},
            {"property": "og:published_time"},
            {"name": "pubdate"},
            {"name": "publish-date"},
        ]

        for tag in meta_tags:
            meta = soup.find("meta", tag)
            if meta and meta.get("content"):
                try:
                    return datetime.fromisoformat(meta["content"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
    except Exception:
        logger.debug("Failed to fetch date from %s", url)

    return None


def extract_date_from_text(text: str) -> datetime | None:
    if not text:
        return None
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        try:
            return datetime.fromisoformat(match.group())
        except (ValueError, TypeError):
            return None
    return None


# ── Filtering & Ranking ──────────────────────────────────────────────────────

_AGGREGATOR_PATTERNS = [
    "mass-layoffs", "layoff-tracker", "layoffs-tracker", "job-cuts",
    "job-losses", "companies-that", "company-list", "list-of", "roundup",
    "weekly-roundup", "monthly-roundup", "latest-updates", "industry-updates",
    "market-update",
]


def is_aggregator_page(url: str) -> bool:
    url_lower = url.lower()
    return any(p in url_lower for p in _AGGREGATOR_PATTERNS)


def is_current_year_url(url: str) -> bool:
    return f"/{datetime.now().year}/" in url


def quick_filter(news: list[dict]) -> list[dict]:
    current_year = datetime.now().year
    old_years = range(2012, current_year - 1)
    filtered: list[dict] = []

    for item in news:
        url = item.get("url", "")
        if any(f"/{year}/" in url for year in old_years):
            continue
        if any(str(year) in url for year in old_years):
            continue
        filtered.append(item)

    return filtered


_RANK_KEYWORDS = [
    "launch", "feature", "product", "update", "new",
    "ai", "platform", "tool", "partnership", "integration",
    "expansion", "growth", "hiring", "strategy",
]


def soft_rank_and_limit(news: list[dict], limit: int = 15) -> list[dict]:
    def score(item: dict) -> int:
        text = (item.get("title", "") + " " + item.get("content", "")).lower()
        s = sum(1 for kw in _RANK_KEYWORDS if kw in text)
        s += min(len(text) // 200, 3)
        return s

    return sorted(news, key=score, reverse=True)[:limit]


def filter_recent_news(results: list[dict], lookback_days: int = 7) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    filtered: list[dict] = []

    for item in results:
        url = item.get("url", "")
        if is_aggregator_page(url):
            continue

        if is_current_year_url(url):
            filtered.append(item)
            continue

        pub_date: datetime | None = None

        if item.get("published_date"):
            try:
                pub_date = datetime.fromisoformat(item["published_date"])
            except (ValueError, TypeError):
                pass

        if not pub_date:
            pub_date = fetch_article_date(url)

        if not pub_date:
            pub_date = extract_date_from_text(item.get("content", ""))

        if pub_date is None:
            continue

        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)

        if pub_date < cutoff:
            continue

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
- Only use the provided data. Order items by impact (highest first) and date (latest to oldest)
- No hallucination
- Max 5 items (Only important ones) - give less if 5 are not very important
- One sentence each

IMPORTANT:
- Focus on important news from the LAST 7 DAYS
- Ignore any news older than 7 days, even if provided.
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
        f"CONTENT: {item.get('content', 'N/A')[:300]}"
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
