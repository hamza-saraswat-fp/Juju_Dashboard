"""
Eval Metrics Page - Charts and trends
"""
import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(page_title="Eval Metrics - Juju", page_icon="📊", layout="wide")

from utils.db import get_metrics_summary, get_daily_metrics, get_question_type_distribution
from utils.charts import (
    create_messages_over_time,
    create_faithfulness_trend,
    create_hallucination_trend,
    create_question_type_pie,
    create_complexity_bar,
    create_high_risk_bar,
    create_faithfulness_histogram,
    create_response_time_chart,
)

st.title("📊 Evaluation Metrics")
st.markdown("Track quality trends and performance over time")

# Get date range from session state
start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date", datetime.now())

# KPIs at top
st.markdown("---")
st.subheader("Key Metrics")

try:
    metrics = get_metrics_summary(start_date=start_date, end_date=end_date)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Messages", metrics["total_messages"])

    with col2:
        st.metric("Messages Today", metrics["messages_today"])

    with col3:
        st.metric("Avg Response Time", f"{metrics['avg_response_time_ms']:.0f}ms")

    with col4:
        faithfulness = metrics["avg_faithfulness"]
        st.metric(
            "Avg Faithfulness",
            f"{faithfulness:.2f}",
            delta="Good" if faithfulness >= 0.8 else "Low",
            delta_color="normal" if faithfulness >= 0.8 else "inverse",
        )

    with col5:
        halluc_rate = metrics["hallucination_rate"]
        st.metric(
            "Hallucination Rate",
            f"{halluc_rate:.1f}%",
            delta="Good" if halluc_rate <= 5 else "High",
            delta_color="normal" if halluc_rate <= 5 else "inverse",
        )

except Exception as e:
    st.error(f"Error loading metrics: {e}")

# Charts
st.markdown("---")
st.subheader("Trends Over Time")

try:
    # Calculate days for daily metrics
    if start_date:
        days = (datetime.now() - start_date).days
    else:
        days = 30

    daily_df = get_daily_metrics(days=days, start_date=start_date, end_date=end_date)

    if not daily_df.empty:
        # Row 1: Messages and Response Time
        col1, col2 = st.columns(2)

        with col1:
            fig = create_messages_over_time(daily_df)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = create_response_time_chart(daily_df)
            st.plotly_chart(fig, use_container_width=True)

        # Row 2: Faithfulness and Hallucination
        col3, col4 = st.columns(2)

        with col3:
            fig = create_faithfulness_trend(daily_df)
            st.plotly_chart(fig, use_container_width=True)

        with col4:
            fig = create_hallucination_trend(daily_df)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for the selected time range.")

except Exception as e:
    st.error(f"Error loading trend data: {e}")

# Distribution charts
st.markdown("---")
st.subheader("Distributions")

try:
    type_df = get_question_type_distribution(start_date=start_date, end_date=end_date)

    if not type_df.empty:
        # Row 1: Question Type and Complexity
        col1, col2 = st.columns(2)

        with col1:
            fig = create_question_type_pie(type_df)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = create_complexity_bar(type_df)
            st.plotly_chart(fig, use_container_width=True)

        # Row 2: High-Risk Topics and Faithfulness Histogram
        col3, col4 = st.columns(2)

        with col3:
            fig = create_high_risk_bar(type_df)
            st.plotly_chart(fig, use_container_width=True)

        with col4:
            # For histogram, we need faithfulness scores
            # Get them from daily metrics or a separate query
            if "faithfulness_score" in type_df.columns:
                fig = create_faithfulness_histogram(type_df)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Faithfulness histogram requires score data.")
    else:
        st.info("No evaluation data available for distributions.")

except Exception as e:
    st.error(f"Error loading distribution data: {e}")

# Raw data view (optional)
st.markdown("---")
with st.expander("📁 View Raw Daily Data"):
    try:
        if not daily_df.empty:
            st.dataframe(daily_df, use_container_width=True)
        else:
            st.info("No data to display.")
    except:
        st.info("No data loaded yet.")
