"""
Juju Dashboard - Main Application
Visualize message history and evaluation metrics
"""
import streamlit as st
from datetime import datetime, timedelta

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Juju Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.db import get_metrics_summary

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e2e8f0;
    }
    .stMetric label {
        color: #64748b;
    }
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🤖 Juju Dashboard")
    st.markdown("---")

    # Date range filter
    st.subheader("Filters")
    date_range = st.selectbox(
        "Time Range",
        ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
        index=1,
    )

    # Calculate date range
    if date_range == "Last 7 days":
        start_date = datetime.now() - timedelta(days=7)
    elif date_range == "Last 30 days":
        start_date = datetime.now() - timedelta(days=30)
    elif date_range == "Last 90 days":
        start_date = datetime.now() - timedelta(days=90)
    else:
        start_date = None

    end_date = datetime.now()

    # Store in session state for pages to access
    st.session_state["start_date"] = start_date
    st.session_state["end_date"] = end_date

    st.markdown("---")

    # Auto-refresh
    st.subheader("Auto-Refresh")
    auto_refresh = st.checkbox("Enable auto-refresh", value=False)
    if auto_refresh:
        refresh_interval = st.selectbox(
            "Refresh every",
            ["30 seconds", "1 minute", "5 minutes"],
            index=1,
        )

        # Convert to seconds
        if refresh_interval == "30 seconds":
            interval_seconds = 30
        elif refresh_interval == "1 minute":
            interval_seconds = 60
        else:
            interval_seconds = 300

        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=interval_seconds * 1000, key="datarefresh")

    st.markdown("---")

    # Quick stats
    st.subheader("Quick Stats")
    try:
        metrics = get_metrics_summary(start_date=start_date, end_date=end_date)
        st.metric("Total Messages", metrics["total_messages"])
        st.metric("Messages Today", metrics["messages_today"])
        st.metric("Avg Faithfulness", f"{metrics['avg_faithfulness']:.2f}")
        st.metric("Hallucination Rate", f"{metrics['hallucination_rate']:.1f}%")
    except Exception as e:
        st.error(f"Could not load metrics: {e}")

# Main content
st.title("Welcome to Juju Dashboard")
st.markdown("""
Use the sidebar to navigate between pages:

- **📋 Message Browser** - Search and explore all Q&A pairs with full evaluation details
- **📊 Eval Metrics** - View charts and trends for faithfulness, hallucinations, and more
- **🚨 Flagged Issues** - Focus on problematic responses that need attention

Select a page from the sidebar to get started.
""")

# Show high-level stats on home page
st.markdown("---")
st.subheader("Overview")

try:
    metrics = get_metrics_summary(start_date=start_date, end_date=end_date)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Messages",
            metrics["total_messages"],
            help="Total Q&A interactions in the selected time range",
        )

    with col2:
        st.metric(
            "Avg Response Time",
            f"{metrics['avg_response_time_ms']:.0f}ms",
            help="Average time to generate a response",
        )

    with col3:
        faithfulness = metrics["avg_faithfulness"]
        st.metric(
            "Avg Faithfulness",
            f"{faithfulness:.2f}",
            delta=f"{'Good' if faithfulness >= 0.8 else 'Needs attention' if faithfulness >= 0.6 else 'Low'}",
            delta_color="normal" if faithfulness >= 0.8 else "inverse",
            help="Average faithfulness score (0-1). Higher is better.",
        )

    with col4:
        halluc_rate = metrics["hallucination_rate"]
        st.metric(
            "Hallucination Rate",
            f"{halluc_rate:.1f}%",
            delta=f"{'Good' if halluc_rate <= 5 else 'Needs attention' if halluc_rate <= 15 else 'High'}",
            delta_color="normal" if halluc_rate <= 5 else "inverse",
            help="Percentage of responses with detected hallucinations",
        )

except Exception as e:
    st.error(f"Error loading dashboard data: {e}")
    st.info("Make sure your Supabase connection is configured correctly in the .env file.")
