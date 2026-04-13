# Joveo Publisher Intelligence Agent

Automated publisher news monitoring service deployed on **Vercel**. Researches job-board publishers daily, generates AI-powered briefs via Gemini, tracks sent URLs in Google Sheets, and delivers digests to Slack.

## Architecture

```
Vercel (Pro)
├── api/
│   ├── cron.py        # Cron endpoint — runs full pipeline (maxDuration: 300s)
│   ├── health.py      # Health check
│   └── schedule.py    # Today's publisher schedule
├── app/
│   ├── config.py      # pydantic-settings config
│   ├── publishers.py  # P0 / P1-P2 publisher lists
│   ├── services.py    # Tavily, Gemini, Slack, Google Sheets
│   └── scheduler.py   # Weekday rotation + job runner
├── vercel.json        # Builds, routes, cron schedule
└── requirements.txt
```

## Schedule

| Day       | Coverage           |
|-----------|--------------------|
| Monday    | P0 publishers      |
| Tuesday   | P1/P2 Batch 1      |
| Wednesday | P1/P2 Batch 2      |
| Thursday  | P0 publishers      |
| Friday    | P1/P2 Batch 3      |
| Sat-Sun   | Skipped            |

Vercel cron runs at **9:00 AM UTC, Mon-Fri**.

## API Endpoints

| Method | Path            | Description                    |
|--------|-----------------|--------------------------------|
| GET    | `/api/health`   | Health check                   |
| GET    | `/api/schedule` | Today's publisher schedule     |
| GET    | `/api/cron`     | Trigger the daily job          |

## Environment Variables (set in Vercel dashboard)

| Variable                  | Required | Description                          |
|---------------------------|----------|--------------------------------------|
| `SLACK_WEBHOOK_URL`       | Yes      | Slack incoming webhook URL           |
| `GEMINI_API_KEY`          | Yes      | Google Gemini API key                |
| `TAVILY_API_KEY`          | Yes      | Tavily search API key                |
| `GOOGLE_CREDENTIALS_JSON` | Yes      | Google service account JSON string   |
| `GOOGLE_SHEET_NAME`       | No       | Sheet name (default: Joveo Intel Logs)|
| `GEMINI_MODEL`            | No       | Model (default: gemini-2.5-flash-lite)|

## Deploy

1. Import the GitHub repo in Vercel
2. Set environment variables in the Vercel dashboard
3. Deploy — cron runs automatically Mon-Fri at 9 AM UTC
