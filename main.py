"""
Juju Dashboard - FastAPI Application
"""
from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime, timedelta
from typing import Optional
import json

from utils.db import (
    get_messages_with_evals,
    get_flagged_messages,
    get_metrics_summary,
    get_daily_metrics,
    get_question_type_distribution,
)

app = FastAPI(title="Juju Dashboard")

# Templates
templates = Jinja2Templates(directory="templates")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


def parse_date_range(range_str: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """Convert date range string to start/end dates."""
    now = datetime.utcnow()  # Use UTC to match database timestamps
    if range_str == "7d":
        start_date = now - timedelta(days=7)
    elif range_str == "30d":
        start_date = now - timedelta(days=30)
    elif range_str == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = None
    return start_date, None  # No end_date filter - we want all messages up to now


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    range: str = Query("30d", description="Date range"),
):
    """Dashboard home page with KPIs."""
    start_date, end_date = parse_date_range(range)

    try:
        metrics = get_metrics_summary(start_date=start_date, end_date=end_date)
    except Exception as e:
        metrics = {
            "total_messages": 0,
            "messages_today": 0,
            "avg_response_time_ms": 0,
            "avg_faithfulness": 0,
            "hallucination_rate": 0,
        }

    return templates.TemplateResponse("index.html", {
        "request": request,
        "metrics": metrics,
        "current_range": range,
        "page": "home",
    })


@app.get("/messages", response_class=HTMLResponse)
async def messages_page(
    request: Request,
    range: str = Query("30d"),
    search: str = Query("", description="Search query"),
    question_type: str = Query("All"),
    complexity: str = Query("All"),
    high_risk: bool = Query(False),
    page: int = Query(1, ge=1),
):
    """Message browser page."""
    start_date, end_date = parse_date_range(range)
    limit = 25
    offset = (page - 1) * limit

    try:
        df = get_messages_with_evals(
            limit=limit,
            offset=offset,
            search=search if search else None,
            start_date=start_date,
            end_date=end_date,
            question_type=question_type if question_type != "All" else None,
            complexity=complexity if complexity != "All" else None,
            high_risk_only=high_risk,
        )
        messages = df.to_dict("records") if not df.empty else []
    except Exception as e:
        messages = []

    return templates.TemplateResponse("messages.html", {
        "request": request,
        "messages": messages,
        "current_range": range,
        "search": search,
        "question_type": question_type,
        "complexity": complexity,
        "high_risk": high_risk,
        "current_page": page,
        "page": "messages",
    })


@app.get("/metrics", response_class=HTMLResponse)
async def metrics_page(
    request: Request,
    range: str = Query("30d"),
):
    """Metrics and charts page."""
    start_date, end_date = parse_date_range(range)

    try:
        metrics = get_metrics_summary(start_date=start_date, end_date=end_date)

        # Get daily data for charts
        days = 30 if range == "30d" else 7 if range == "7d" else 90
        daily_df = get_daily_metrics(days=days, start_date=start_date, end_date=end_date)
        daily_data = daily_df.to_dict("records") if not daily_df.empty else []

        # Convert dates to strings for JSON
        for row in daily_data:
            if "date" in row:
                row["date"] = str(row["date"])

        # Get distributions
        dist_df = get_question_type_distribution(start_date=start_date, end_date=end_date)

        # Question type counts
        if not dist_df.empty and "question_type" in dist_df.columns:
            type_counts = dist_df["question_type"].value_counts().to_dict()
        else:
            type_counts = {}

        # Complexity counts
        if not dist_df.empty and "question_complexity" in dist_df.columns:
            complexity_counts = dist_df["question_complexity"].value_counts().to_dict()
        else:
            complexity_counts = {}

    except Exception as e:
        metrics = {"total_messages": 0, "messages_today": 0, "avg_response_time_ms": 0, "avg_faithfulness": 0, "hallucination_rate": 0}
        daily_data = []
        type_counts = {}
        complexity_counts = {}

    return templates.TemplateResponse("metrics.html", {
        "request": request,
        "metrics": metrics,
        "daily_data": json.dumps(daily_data),
        "type_counts": json.dumps(type_counts),
        "complexity_counts": json.dumps(complexity_counts),
        "current_range": range,
        "page": "metrics",
    })


@app.get("/flagged", response_class=HTMLResponse)
async def flagged_page(
    request: Request,
    range: str = Query("30d"),
    threshold: float = Query(0.7, ge=0, le=1),
):
    """Flagged issues page."""
    start_date, end_date = parse_date_range(range)

    try:
        df = get_flagged_messages(
            limit=100,
            faithfulness_threshold=threshold,
            start_date=start_date,
            end_date=end_date,
        )
        flagged = df.to_dict("records") if not df.empty else []

        # Calculate summary stats
        if flagged:
            halluc_count = sum(1 for m in flagged if m.get("hallucination_detected"))
            cap_halluc_count = sum(1 for m in flagged if m.get("capability_hallucination"))
            low_faith_count = sum(1 for m in flagged if (m.get("faithfulness_score") or 1) < threshold)
            bad_citation_count = sum(1 for m in flagged if m.get("citation_accurate") == False)
        else:
            halluc_count = cap_halluc_count = low_faith_count = bad_citation_count = 0

    except Exception as e:
        flagged = []
        halluc_count = cap_halluc_count = low_faith_count = bad_citation_count = 0

    return templates.TemplateResponse("flagged.html", {
        "request": request,
        "flagged": flagged,
        "halluc_count": halluc_count,
        "cap_halluc_count": cap_halluc_count,
        "low_faith_count": low_faith_count,
        "bad_citation_count": bad_citation_count,
        "threshold": threshold,
        "current_range": range,
        "page": "flagged",
    })


# API endpoints for async data loading
@app.get("/api/metrics")
async def api_metrics(range: str = Query("30d")):
    """API endpoint for metrics data."""
    start_date, end_date = parse_date_range(range)
    try:
        metrics = get_metrics_summary(start_date=start_date, end_date=end_date)
        return JSONResponse(metrics)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/daily")
async def api_daily(range: str = Query("30d")):
    """API endpoint for daily chart data."""
    start_date, end_date = parse_date_range(range)
    days = 30 if range == "30d" else 7 if range == "7d" else 90
    try:
        df = get_daily_metrics(days=days, start_date=start_date, end_date=end_date)
        data = df.to_dict("records") if not df.empty else []
        for row in data:
            if "date" in row:
                row["date"] = str(row["date"])
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
