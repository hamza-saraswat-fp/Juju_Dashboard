"""
Supabase database utilities for Juju Dashboard
"""
import os
from typing import Optional
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_client() -> Client:
    """Get Supabase client instance."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_messages(
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """Fetch messages from juju_messages table."""
    client = get_client()

    query = client.table("juju_messages").select("*")

    if start_date:
        query = query.gte("created_at", start_date.isoformat())
    if end_date:
        query = query.lte("created_at", end_date.isoformat())

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

    response = query.execute()
    df = pd.DataFrame(response.data)

    if search and not df.empty:
        mask = (
            df["question"].str.contains(search, case=False, na=False) |
            df["response"].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    return df


def get_evaluations(message_ids: list) -> pd.DataFrame:
    """Fetch evaluations for specific message IDs."""
    if not message_ids:
        return pd.DataFrame()

    client = get_client()
    response = client.table("juju_evaluations").select("*").in_("message_id", message_ids).execute()
    return pd.DataFrame(response.data)


def get_messages_with_evals(
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    question_type: Optional[str] = None,
    complexity: Optional[str] = None,
    high_risk_only: bool = False,
) -> pd.DataFrame:
    """Fetch messages joined with their evaluations."""
    client = get_client()

    # Fetch messages
    messages_query = client.table("juju_messages").select("*")

    if start_date:
        messages_query = messages_query.gte("created_at", start_date.isoformat())
    if end_date:
        messages_query = messages_query.lte("created_at", end_date.isoformat())

    messages_query = messages_query.order("created_at", desc=True).range(offset, offset + limit - 1)
    messages_response = messages_query.execute()
    messages_df = pd.DataFrame(messages_response.data)

    if messages_df.empty:
        return messages_df

    # Fetch evaluations for these messages
    message_ids = messages_df["id"].tolist()
    evals_response = client.table("juju_evaluations").select("*").in_("message_id", message_ids).execute()
    evals_df = pd.DataFrame(evals_response.data)

    if evals_df.empty:
        return messages_df

    # Merge
    merged = messages_df.merge(evals_df, left_on="id", right_on="message_id", how="left", suffixes=("", "_eval"))

    # Apply filters
    if search:
        mask = (
            merged["question"].str.contains(search, case=False, na=False) |
            merged["response"].str.contains(search, case=False, na=False)
        )
        merged = merged[mask]

    if question_type and question_type != "All":
        merged = merged[merged["question_type"] == question_type]

    if complexity and complexity != "All":
        merged = merged[merged["question_complexity"] == complexity]

    if high_risk_only:
        merged = merged[merged["is_high_risk_topic"] == True]

    return merged


def get_flagged_messages(
    limit: int = 100,
    faithfulness_threshold: float = 0.7,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """Fetch messages with issues (hallucinations, low scores, etc.)."""
    client = get_client()

    # Get all evaluations with issues
    evals_query = client.table("juju_evaluations").select("*")

    # We'll filter in pandas since Supabase doesn't support complex OR queries well
    evals_response = evals_query.execute()
    evals_df = pd.DataFrame(evals_response.data)

    if evals_df.empty:
        return evals_df

    # Filter for flagged issues
    mask = (
        (evals_df["hallucination_detected"] == True) |
        (evals_df["capability_hallucination"] == True) |
        (evals_df["faithfulness_score"].fillna(1) < faithfulness_threshold) |
        (evals_df["citation_accurate"] == False)
    )
    flagged_evals = evals_df[mask]

    if flagged_evals.empty:
        return pd.DataFrame()

    # Get the corresponding messages
    message_ids = flagged_evals["message_id"].tolist()
    messages_query = client.table("juju_messages").select("*").in_("id", message_ids)

    if start_date:
        messages_query = messages_query.gte("created_at", start_date.isoformat())
    if end_date:
        messages_query = messages_query.lte("created_at", end_date.isoformat())

    messages_query = messages_query.order("created_at", desc=True).limit(limit)
    messages_response = messages_query.execute()
    messages_df = pd.DataFrame(messages_response.data)

    if messages_df.empty:
        return messages_df

    # Merge
    merged = messages_df.merge(flagged_evals, left_on="id", right_on="message_id", how="inner", suffixes=("", "_eval"))

    return merged


def get_metrics_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """Get aggregate metrics for the dashboard."""
    client = get_client()

    # Get messages
    messages_query = client.table("juju_messages").select("id, created_at, response_time_ms")
    if start_date:
        messages_query = messages_query.gte("created_at", start_date.isoformat())
    if end_date:
        messages_query = messages_query.lte("created_at", end_date.isoformat())

    messages_response = messages_query.execute()
    messages_df = pd.DataFrame(messages_response.data)

    if messages_df.empty:
        return {
            "total_messages": 0,
            "avg_response_time_ms": 0,
            "avg_faithfulness": 0,
            "hallucination_rate": 0,
            "messages_today": 0,
        }

    # Get evaluations
    message_ids = messages_df["id"].tolist()
    evals_response = client.table("juju_evaluations").select("*").in_("message_id", message_ids).execute()
    evals_df = pd.DataFrame(evals_response.data)

    # Calculate metrics
    total_messages = len(messages_df)
    avg_response_time = messages_df["response_time_ms"].mean() if "response_time_ms" in messages_df.columns else 0

    # Today's messages
    today = datetime.utcnow().date()  # Use UTC to match database timestamps
    if "created_at" in messages_df.columns:
        messages_df["date"] = pd.to_datetime(messages_df["created_at"]).dt.date
        messages_today = len(messages_df[messages_df["date"] == today])
    else:
        messages_today = 0

    # Eval metrics
    if not evals_df.empty:
        avg_faithfulness = evals_df["faithfulness_score"].mean() if "faithfulness_score" in evals_df.columns else 0
        hallucination_count = evals_df["hallucination_detected"].sum() if "hallucination_detected" in evals_df.columns else 0
        hallucination_rate = hallucination_count / len(evals_df) if len(evals_df) > 0 else 0
    else:
        avg_faithfulness = 0
        hallucination_rate = 0

    return {
        "total_messages": total_messages,
        "avg_response_time_ms": round(avg_response_time or 0, 0),
        "avg_faithfulness": round(avg_faithfulness or 0, 3),
        "hallucination_rate": round(hallucination_rate * 100, 1),
        "messages_today": messages_today,
    }


def get_daily_metrics(
    days: int = 30,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """Get daily aggregated metrics for charts."""
    client = get_client()

    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=days)
    # Don't set default end_date - we want all messages up to now

    # Get messages
    query = client.table("juju_messages").select(
        "id, created_at, response_time_ms"
    ).gte("created_at", start_date.isoformat())

    if end_date:  # Only filter end_date if explicitly provided
        query = query.lte("created_at", end_date.isoformat())

    messages_response = query.execute()

    messages_df = pd.DataFrame(messages_response.data)

    if messages_df.empty:
        return pd.DataFrame()

    messages_df["date"] = pd.to_datetime(messages_df["created_at"]).dt.date

    # Get evaluations
    message_ids = messages_df["id"].tolist()
    evals_response = client.table("juju_evaluations").select("*").in_("message_id", message_ids).execute()
    evals_df = pd.DataFrame(evals_response.data)

    # Rename id before merge to avoid conflicts
    messages_df = messages_df.rename(columns={"id": "msg_id"})

    # Merge
    if not evals_df.empty:
        merged = messages_df.merge(evals_df, left_on="msg_id", right_on="message_id", how="left")
    else:
        merged = messages_df.copy()
        merged["faithfulness_score"] = None
        merged["hallucination_detected"] = False

    # Aggregate by date
    daily = merged.groupby("date").agg({
        "msg_id": "count",
        "response_time_ms": "mean",
        "faithfulness_score": "mean",
        "hallucination_detected": lambda x: x.sum() / len(x) * 100 if len(x) > 0 else 0,
    }).reset_index()

    daily.columns = ["date", "message_count", "avg_response_time", "avg_faithfulness", "hallucination_rate"]
    daily = daily.sort_values("date")

    return daily


def get_question_type_distribution(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """Get distribution of question types."""
    client = get_client()

    evals_query = client.table("juju_evaluations").select("question_type, question_complexity, is_high_risk_topic, high_risk_category")

    # Note: We'd need to join with messages for date filtering, simplified here
    evals_response = evals_query.execute()
    evals_df = pd.DataFrame(evals_response.data)

    if evals_df.empty:
        return pd.DataFrame()

    return evals_df
