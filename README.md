# Joveo Publisher Intelligence Agent

Automated publisher news monitoring service that researches job-board publishers daily, generates AI-powered briefs via Gemini, and delivers them to Slack.

## Architecture

```
Publisher-Intel/
├── app/
│   ├── main.py          # FastAPI app, scheduler, routes
│   ├── config.py        # pydantic-settings config
│   ├── publishers.py    # P0 / P1-P2 publisher lists
│   ├── services.py      # Tavily search, Gemini analysis, Slack
│   └── scheduler.py     # Weekday rotation + job runner
├── run.py               # CLI one-shot runner
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
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

P1/P2 batches rotate weekly so all publishers get covered.

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd Publisher-Intel
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run

**API server (with built-in scheduler):**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**One-shot CLI run:**

```bash
python run.py
```

**Docker:**

```bash
docker compose up -d
```

## API Endpoints

| Method | Path        | Description                          |
|--------|-------------|--------------------------------------|
| GET    | `/health`   | Health check                         |
| GET    | `/schedule` | Today's publisher schedule           |
| POST   | `/run-job`  | Manually trigger the daily job       |

## Environment Variables

| Variable                | Required | Default           |
|-------------------------|----------|-------------------|
| `SLACK_WEBHOOK_URL`     | Yes      | —                 |
| `GEMINI_API_KEY`        | Yes      | —                 |
| `TAVILY_API_KEY`        | Yes      | —                 |
| `GEMINI_MODEL`          | No       | `gemini-2.5-flash`|
| `TAVILY_MAX_RESULTS`    | No       | `3`               |
| `TAVILY_SEARCH_DEPTH`   | No       | `advanced`        |
| `NEWS_LOOKBACK_DAYS`    | No       | `7`               |
| `PUBLISHER_SEARCH_LIMIT`| No       | `12`              |
| `CRON_HOUR`             | No       | `9`               |
| `CRON_MINUTE`           | No       | `0`               |
| `PORT`                  | No       | `8000`            |
