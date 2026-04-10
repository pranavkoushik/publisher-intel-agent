"""
Joveo Publisher Intelligence Agent
Runs daily, researches publisher partners, posts Slack digest.
Uses Tavily for real-time search + Gemini for analysis.
"""

import os
import json
import datetime
import requests
import google.generativeai as genai
from tavily import TavilyClient

# ── Config ────────────────────────────────────────────────────────────────────
# Shubhankar's Gemini API Key
GEMINI_API_KEY = "AIzaSyBsMmTsHq8QNdxkkXx3oANpoIB5XvDihJ0"
# Supply Partnership Product Channel
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
# Shubhankar's Tavily API Key
TAVILY_API_KEY = "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"
GEMINI_MODEL = "gemini-2.5-flash"

genai.configure(api_key=GEMINI_API_KEY)
tavily = TavilyClient(api_key=TAVILY_API_KEY)

# ── Publisher Lists ───────────────────────────────────────────────────────────
P0_PUBLISHERS = [
    "employers.io", "Joblift", "JobGet", "Snagajob", "Jobcase",
    "Monster", "Allthetopbananas", "JobRapido", "Talent.com", "Talroo",
    "ZipRecruiter", "OnTimeHire", "Indeed", "Sercanto", "YadaJobs",
    "Hokify", "Upward.net", "JobCloud", "Jooble", "Nurse.com",
    "Geographic Solutions", "Reed", "Jobbsafari.se", "Jobbland",
    "Handshake", "1840"
]

P1_P2_PUBLISHERS = [
    "JobSwipe", "Jobbird.de", "Tideri", "Manymore.jobs", "ClickaJobs",
    "MyJobScanner", "Job Traffic", "Jobtome", "Propel", "AllJobs",
    "Jora", "EarnBetter", "WhatJobs", "J-Vers", "Adzuna",
    "Galois", "Mindmatch.ai", "Myjobhelper", "TransForce", "CV Library",
    "CDLlife", "PlacedApp", "IrishJobs", "Praca.pl", "AppJobs",
    "OfferUp", "JobsInNetwork", "Jobsora", "StellenSMS", "Dice",
    "SonicJobs", "Botson.ai", "CMP Jobs", "Health Ecareers", "Hokify",
    "JobHubCentral", "BoostPoint", "Jobs In Japan", "Daijob.com",
    "GaijinPot", "GoWork.pl", "deBanenSite.nl", "Pracuj.pl", "Xing",
    "PostJobFree", "Jobsdb", "Stellenanzeigen.de", "Jobs.at", "Jobs.ch",
    "JobUp", "Jobwinner", "Topjobs.ch", "Vetted Health", "Arya by Leoforce",
    "Welcome to the Jungle", "JobMESH", "Bakeca.it", "Stack Overflow",
    "Diversity Jobs", "Laborum", "Curriculum", "American Nurses Association",
    "Profesia", "CareerCross", "Jobs.ie", "Nexxt", "Resume-Library.com",
    "Women for Hire", "Professional Diversity Network", "Rabota.bg",
    "Zaplata.bg", "Jobnet", "New Zealand Jobs", "Nationale Vacaturebank",
    "Intermediair", "eFinancialCareers", "Profession.hu", "Job Bank",
    "Personalwerk", "Yapo", "Karriere.at", "SAPO Emprego", "Catho",
    "Totaljobs", "Handshake", "Ladders.com", "Gumtree", "Instawork",
    "LinkedIn", "Facebook", "Instagram", "Google Ads", "Craigslist",
    "Reddit", "YouTube", "Spotify", "Jobbland", "Wonderkind",
    "adway.ai", "HeyTempo", "Otta", "Info Jobs", "Vagas",
    "Visage Jobs", "Hunar.ai", "CollabWORK", "Arbeitnow", "Doximity",
    "VietnamWorks", "JobKorea", "JobIndex", "HH.ru", "Consultants 500",
    "YM Careers", "Dental Post", "Foh and Boh", "Study Smarter",
    "Pnet", "Remote.co", "FATj", "Expresso Emprego", "Bravado"
]

# Sort P1/P2 alphabetically and split into 3 batches
P1_P2_SORTED = sorted(P1_P2_PUBLISHERS)
BATCH_SIZE = len(P1_P2_SORTED) // 3
P1_P2_BATCHES = [
    P1_P2_SORTED[:BATCH_SIZE],
    P1_P2_SORTED[BATCH_SIZE:BATCH_SIZE * 2],
    P1_P2_SORTED[BATCH_SIZE * 2:]
]


# ── Schedule Logic ────────────────────────────────────────────────────────────
def get_todays_publishers():
    today = datetime.date.today()
    weekday = today.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri

    # Week number determines which P1/P2 batch rotation we're in
    week_num = today.isocalendar()[1]

    schedule = {
        0: ("P0", P0_PUBLISHERS, "P0 publishers", "P1/P2 Batch 1 Tuesday"),
        1: ("P1/P2 Batch 1", P1_P2_BATCHES[(week_num) % 3], "P1/P2 Batch 1", "P1/P2 Batch 2 Wednesday"),
        2: ("P1/P2 Batch 2", P1_P2_BATCHES[(week_num + 1) % 3], "P1/P2 Batch 2", "P1/P2 Batch 3 Friday"),
        3: ("P0", P0_PUBLISHERS, "P0 publishers", "P1/P2 Batch 3 Friday"),
        4: ("P1/P2 Batch 3", P1_P2_BATCHES[(week_num + 2) % 3], "P1/P2 Batch 3", "P0 publishers Monday"),
    }

    if weekday not in schedule:
        return None, None, None, None

    label, publishers, coverage_label, next_label = schedule[weekday]
    return label, publishers, coverage_label, next_label


# ── Tavily Search ─────────────────────────────────────────────────────────────
def fetch_news(publishers):
    all_results = []

    for pub in publishers[:12]:  # limit for speed
        query = f"{pub} funding OR acquisition OR hiring OR layoffs OR product launch OR pricing changes OR new location OR new expansions last 7 days"

        try:
            results = tavily.search(
                query=query,
                search_depth="advanced",
                max_results=3,
                days = 7
            )
            all_results.extend(results["results"])
        except Exception as e:
            print(f"Search failed for {pub}: {e}")

    return all_results

from datetime import datetime as dt, timedelta

def filter_recent_news(results):
    filtered = []
    cutoff = dt.now() - timedelta(days=7)

    for item in results:
        if "published_date" in item and item["published_date"]:
            try:
                pub_date = dt.fromisoformat(item["published_date"])
                if pub_date >= cutoff:
                    filtered.append(item)
            except:
                filtered.append(item)  # fallback if parsing fails
        else:
            filtered.append(item)

    return filtered

# ── Gemini Processing ─────────────────────────────────────────────────────────
def generate_brief(news_data, coverage_label):
    today = datetime.date.today().strftime("%A, %d %B %Y")

    context = "\n\n".join([
        f"TITLE: {item['title']}\nURL: {item['url']}\nCONTENT: {item['content']}"
        for item in news_data
    ])

    prompt = f"""
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

    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)

    return response.text.strip()

def deduplicate_news(results):
    seen_urls = set()
    unique = []

    for item in results:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            unique.append(item)

    return unique

# ── Slack ─────────────────────────────────────────────────────────────────────
def post_to_slack(message):
    response = requests.post(
        SLACK_WEBHOOK_URL,
        data=json.dumps({"text": message}),
        headers={"Content-Type": "application/json"}
    )
    return response.status_code == 200

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Starting Publisher Intel...")

    label, publishers, coverage_label, _ = get_todays_publishers()
    # label = "P1/P2 Test"
    # publishers = P1_P2_PUBLISHERS
    # coverage_label = "P1/P2 publishers"

    if publishers is None:
        print("Weekend — skipping")
        return

    print("Fetching real-time news...")
    news = fetch_news(publishers)
    news = filter_recent_news(news)
    news = deduplicate_news(news)

    print(f"Collected {len(news)} news items")

    if not news:
        print("No news found — exiting")
        return

    print("Generating brief...")
    brief = generate_brief(news, coverage_label)

    print("Posting to Slack...")
    post_to_slack(brief)

    print("Done.")

if __name__ == "__main__":
    main()