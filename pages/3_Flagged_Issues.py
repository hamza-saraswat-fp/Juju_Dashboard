"""
Flagged Issues Page - Focus on problematic responses
"""
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Flagged Issues - Juju", page_icon="🚨", layout="wide")

from utils.db import get_flagged_messages

st.title("🚨 Flagged Issues")
st.markdown("Review responses with detected issues that need attention")

# Get date range from session state
start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date", datetime.now())

# Filters
st.markdown("---")
col1, col2 = st.columns([1, 3])

with col1:
    faithfulness_threshold = st.slider(
        "Faithfulness threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Show messages with faithfulness below this score",
    )

with col2:
    st.markdown("""
    **Flagged conditions:**
    - 🔴 Hallucination detected
    - 🔴 Capability hallucination (false product claims)
    - 🟡 Low faithfulness score (below threshold)
    - 🟡 Inaccurate citations
    """)

# Fetch flagged messages
with st.spinner("Loading flagged issues..."):
    try:
        df = get_flagged_messages(
            limit=100,
            faithfulness_threshold=faithfulness_threshold,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        st.error(f"Error loading data: {e}")
        df = pd.DataFrame()

# Summary stats
if not df.empty:
    st.markdown("---")
    st.subheader("Issue Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        halluc_count = df["hallucination_detected"].sum() if "hallucination_detected" in df.columns else 0
        st.metric("🔴 Hallucinations", int(halluc_count))

    with col2:
        cap_halluc_count = df["capability_hallucination"].sum() if "capability_hallucination" in df.columns else 0
        st.metric("🔴 Capability Hallucinations", int(cap_halluc_count))

    with col3:
        low_faith_count = len(df[df["faithfulness_score"] < faithfulness_threshold]) if "faithfulness_score" in df.columns else 0
        st.metric("🟡 Low Faithfulness", low_faith_count)

    with col4:
        bad_citations = len(df[df["citation_accurate"] == False]) if "citation_accurate" in df.columns else 0
        st.metric("🟡 Bad Citations", bad_citations)

# Display flagged issues
st.markdown("---")
st.subheader("Flagged Messages")

if df.empty:
    st.success("🎉 No flagged issues found! All responses look good.")
else:
    st.warning(f"Found **{len(df)} flagged issues** that need review")

    for idx, row in df.iterrows():
        # Determine severity
        issues = []
        severity = "warning"

        if row.get("hallucination_detected"):
            issues.append("🔴 Hallucination")
            severity = "error"
        if row.get("capability_hallucination"):
            issues.append("🔴 Capability Hallucination")
            severity = "error"
        if row.get("faithfulness_score") and row["faithfulness_score"] < faithfulness_threshold:
            issues.append(f"🟡 Low Faithfulness ({row['faithfulness_score']:.2f})")
        if row.get("citation_accurate") == False:
            issues.append("🟡 Inaccurate Citations")

        issue_str = " | ".join(issues)
        question_preview = str(row.get("question", ""))[:80] + "..." if len(str(row.get("question", ""))) > 80 else str(row.get("question", ""))

        with st.expander(f"{issue_str} — {question_preview}", expanded=False):
            # Timestamp and metadata
            col_time, col_type = st.columns(2)
            with col_time:
                st.caption(f"📅 {row.get('created_at', 'Unknown')}")
            with col_type:
                q_type = row.get("question_type", "N/A")
                risk = "⚠️ HIGH-RISK" if row.get("is_high_risk_topic") else ""
                st.caption(f"Type: {q_type} {risk}")

            st.markdown("---")

            # Question
            st.markdown("**Question:**")
            st.info(row.get("question", "N/A"))

            # Response
            st.markdown("**Response:**")
            response = row.get("response", "N/A")
            if severity == "error":
                st.error(response)
            else:
                st.warning(response)

            # Evaluation details
            st.markdown("---")
            st.markdown("**Evaluation Details:**")

            # Scores
            score_cols = st.columns(4)
            with score_cols[0]:
                faith = row.get("faithfulness_score")
                if faith is not None:
                    color = "red" if faith < 0.6 else "orange" if faith < 0.8 else "green"
                    st.markdown(f"Faithfulness: :{color}[**{faith:.2f}**]")
            with score_cols[1]:
                comp = row.get("completeness_score")
                if comp is not None:
                    st.markdown(f"Completeness: **{comp:.2f}**")
            with score_cols[2]:
                clarity = row.get("clarity_score")
                if clarity is not None:
                    st.markdown(f"Clarity: **{clarity:.2f}**")
            with score_cols[3]:
                citation = row.get("citation_accurate")
                if citation is not None:
                    st.markdown(f"Citations OK: {'✅' if citation else '❌'}")

            # Hallucination reasoning
            if row.get("hallucination_detected") or row.get("capability_hallucination"):
                st.markdown("---")
                st.markdown("**🔍 Hallucination Analysis:**")
                reasoning = row.get("hallucination_reasoning")
                if reasoning:
                    st.error(reasoning)
                else:
                    st.error("Hallucination detected but no reasoning provided.")

            # Faithfulness reasoning
            faith_reasoning = row.get("faithfulness_reasoning")
            if faith_reasoning and row.get("faithfulness_score", 1) < faithfulness_threshold:
                st.markdown("---")
                st.markdown("**🔍 Faithfulness Analysis:**")
                st.warning(faith_reasoning)

            # Overall assessment
            assessment = row.get("overall_assessment")
            if assessment:
                st.markdown("---")
                st.markdown("**Overall Assessment:**")
                st.info(assessment)

            # Sources cited (for checking citation accuracy)
            sources = row.get("sources_cited")
            if sources:
                st.markdown("---")
                st.markdown("**Sources Cited:**")
                if isinstance(sources, list):
                    for source in sources:
                        if isinstance(source, dict):
                            title = source.get("title", "Unknown")
                            url = source.get("url", "#")
                            st.markdown(f"- [{title}]({url})")
                        else:
                            st.markdown(f"- {source}")

            # Action buttons placeholder
            st.markdown("---")
            col_actions = st.columns(3)
            with col_actions[0]:
                if st.button("📝 Mark Reviewed", key=f"review_{idx}"):
                    st.success("Marked as reviewed (not persisted - add DB logic)")
            with col_actions[1]:
                thread_ts = row.get("slack_thread_ts")
                channel = row.get("slack_channel")
                if thread_ts and channel:
                    st.caption(f"Slack: #{channel} / {thread_ts}")

# Export option
st.markdown("---")
with st.expander("📥 Export Flagged Issues"):
    if not df.empty:
        # Select columns for export
        export_cols = ["created_at", "question", "response", "faithfulness_score",
                       "hallucination_detected", "capability_hallucination",
                       "hallucination_reasoning", "faithfulness_reasoning"]
        export_cols = [c for c in export_cols if c in df.columns]
        export_df = df[export_cols]

        csv = export_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"juju_flagged_issues_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No data to export.")
