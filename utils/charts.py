"""
Reusable chart components for Juju Dashboard
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def create_messages_over_time(df: pd.DataFrame) -> go.Figure:
    """Line chart of messages over time."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    fig = px.line(
        df,
        x="date",
        y="message_count",
        title="Messages Over Time",
        labels={"date": "Date", "message_count": "Messages"},
    )
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(line_color="#4F46E5", line_width=2)
    return fig


def create_faithfulness_trend(df: pd.DataFrame) -> go.Figure:
    """Line chart of average faithfulness score over time."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    fig = px.line(
        df,
        x="date",
        y="avg_faithfulness",
        title="Faithfulness Score Trend",
        labels={"date": "Date", "avg_faithfulness": "Avg Faithfulness"},
    )
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(range=[0, 1]),
    )
    fig.update_traces(line_color="#10B981", line_width=2)
    return fig


def create_hallucination_trend(df: pd.DataFrame) -> go.Figure:
    """Line chart of hallucination rate over time."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    fig = px.line(
        df,
        x="date",
        y="hallucination_rate",
        title="Hallucination Rate Trend",
        labels={"date": "Date", "hallucination_rate": "Hallucination Rate (%)"},
    )
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(line_color="#EF4444", line_width=2)
    return fig


def create_question_type_pie(df: pd.DataFrame) -> go.Figure:
    """Pie chart of question type distribution."""
    if df.empty or "question_type" not in df.columns:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    type_counts = df["question_type"].value_counts().reset_index()
    type_counts.columns = ["question_type", "count"]

    fig = px.pie(
        type_counts,
        values="count",
        names="question_type",
        title="Question Type Distribution",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_complexity_bar(df: pd.DataFrame) -> go.Figure:
    """Bar chart of question complexity distribution."""
    if df.empty or "question_complexity" not in df.columns:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    complexity_counts = df["question_complexity"].value_counts().reset_index()
    complexity_counts.columns = ["complexity", "count"]

    # Order: simple, moderate, complex
    order = ["simple", "moderate", "complex"]
    complexity_counts["complexity"] = pd.Categorical(
        complexity_counts["complexity"], categories=order, ordered=True
    )
    complexity_counts = complexity_counts.sort_values("complexity")

    fig = px.bar(
        complexity_counts,
        x="complexity",
        y="count",
        title="Question Complexity",
        labels={"complexity": "Complexity", "count": "Count"},
        color="complexity",
        color_discrete_map={
            "simple": "#10B981",
            "moderate": "#F59E0B",
            "complex": "#EF4444",
        },
    )
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_high_risk_bar(df: pd.DataFrame) -> go.Figure:
    """Bar chart of high-risk category distribution."""
    if df.empty or "high_risk_category" not in df.columns:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    # Filter to only high-risk entries
    high_risk_df = df[df["is_high_risk_topic"] == True]

    if high_risk_df.empty:
        return go.Figure().add_annotation(text="No high-risk topics found", showarrow=False)

    category_counts = high_risk_df["high_risk_category"].value_counts().reset_index()
    category_counts.columns = ["category", "count"]

    fig = px.bar(
        category_counts,
        x="category",
        y="count",
        title="High-Risk Topic Categories",
        labels={"category": "Category", "count": "Count"},
        color_discrete_sequence=["#EF4444"],
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_faithfulness_histogram(df: pd.DataFrame) -> go.Figure:
    """Histogram of faithfulness scores."""
    if df.empty or "faithfulness_score" not in df.columns:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    scores = df["faithfulness_score"].dropna()

    if scores.empty:
        return go.Figure().add_annotation(text="No faithfulness scores available", showarrow=False)

    fig = px.histogram(
        scores,
        nbins=20,
        title="Faithfulness Score Distribution",
        labels={"value": "Faithfulness Score", "count": "Count"},
        color_discrete_sequence=["#4F46E5"],
    )
    fig.update_layout(
        xaxis=dict(range=[0, 1]),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def create_response_time_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart of average response time over time."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    fig = px.line(
        df,
        x="date",
        y="avg_response_time",
        title="Average Response Time",
        labels={"date": "Date", "avg_response_time": "Response Time (ms)"},
    )
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(line_color="#8B5CF6", line_width=2)
    return fig
