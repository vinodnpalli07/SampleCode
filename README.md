# Test Run Analysis Agent

Python/ FastAPI service that ingests Bamboo test run results, extracts common failure signatures, persists them to MongoDB, and exposes an HTML dashboard for reporting.

## Features

- Pull Bamboo run metadata and logs via REST API and auto-extract failure buckets.
- Persist runs, error signatures, and aggregated metrics in MongoDB for historical analysis.
- REST API to ingest runs programmatically (`POST /api/runs`) and retrieve insights (`/api/dashboard/*`).
- Single-page dashboard (Chart.js + FastAPI templates) with KPIs, recent runs, and top errors.
- CLI scripts to bootstrap indexes and batch-ingest Bamboo runs by result key.

## Project Layout

```
app/
  api/              # FastAPI routers
  services/         # Bamboo ingestion, persistence, analytics
  models/           # Pydantic schemas
  static/           # Dashboard assets (CSS, JS)
  templates/        # Jinja2 HTML templates
scripts/            # Utility scripts (init DB, ingest runs)
```

## Getting Started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment** (create `.env`)

   ```ini
   MONGO_URI=mongodb://localhost:27017
   MONGO_DATABASE=test_run_analytics
   BAMBOO_BASE_URL=https://bamboo.example.com
   BAMBOO_USERNAME=your-username
   BAMBOO_PASSWORD=your-password-or-pat
   # Optional personal access token alternative
   # BAMBOO_PAT=your-token
   ```

3. **Initialise database indexes**

   ```bash
   python scripts/init_db.py
   ```

4. **Run the API & dashboard**

   ```bash
   uvicorn app.main:app --reload
   ```

   Visit [http://localhost:8000](http://localhost:8000) for the dashboard.

## Ingesting Bamboo Runs

- **On-demand via CLI**

  ```bash
  python scripts/ingest_bamboo_runs.py PLAN-KEY-123 PLAN-KEY-124
  ```

- **Automated via API** (called at end of test run)

  ```bash
  curl -X POST http://localhost:8000/api/runs \
       -H "Content-Type: application/json" \
       -d '{
             "run_id": "PLAN-KEY-125",
             "plan": "PLAN",
             "status": "FAILED",
             "start_time": "2025-10-30T12:00:00Z",
             "end_time": "2025-10-30T12:25:00Z",
             "total_tests": 120,
             "passed_tests": 110,
             "failed_tests": 10,
             "bamboo_result_key": "PLAN-KEY-125"
           }'
  ```

  The service fetches the full log, extracts failure signatures, and persists them.

## Dashboard API Reference

- `GET /api/dashboard/summary` — KPI totals (supports filters: plan, suite, environment, owner, status, from, to).
- `GET /api/dashboard/recent-runs` — latest runs with aggregated metrics.
- `GET /api/dashboard/common-errors` — most frequent error signatures.
- `GET /api/dashboard/error-trends` — signature occurrence trends across runs.

## Extending

- Add authentication (e.g. API keys) before exposing publicly.
- Attach analytics jobs (e.g. daily cron) to compute historical trends.
- Enhance log parsing with ML-based clustering for richer error categorisation.
- Integrate with work-item trackers to correlate failures with bugs.

