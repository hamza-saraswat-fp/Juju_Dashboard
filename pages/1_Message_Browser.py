"""
Message Browser Page - Search and explore Q&A pairs
"""
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Message Browser - Juju", page_icon="📋", layout="wide")

from utils.db import get_messages_with_evals

st.title("📋 Message Browser")
st.markdown("Search and explore all Q&A pairs with evaluation details")

# Get date range from session state
start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date", datetime.now())

# Filters
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

with col1:
    search = st.text_input("🔍 Search questions or responses", placeholder="Type to search...")

with col2:
    question_type = st.selectbox(
        "Question Type",
        ["All", "how_to", "can_we", "what_is", "troubleshooting", "pricing", "integration", "other"],
    )

with col3:
    complexity = st.selectbox(
        "Complexity",
        ["All", "simple", "moderate", "complex"],
    )

with col4:
    high_risk_only = st.checkbox("High-risk only", value=False)

# Pagination
st.markdown("---")
col_page, col_limit = st.columns([1, 1])
with col_page:
    page = st.number_input("Page", min_value=1, value=1, step=1)
with col_limit:
    limit = st.selectbox("Results per page", [25, 50, 100], index=0)

offset = (page - 1) * limit

# Fetch data
with st.spinner("Loading messages..."):
    try:
        df = get_messages_with_evals(
            limit=limit,
            offset=offset,
            search=search if search else None,
            start_date=start_date,
            end_date=end_date,
            question_type=question_type if question_type != "All" else None,
            complexity=complexity if complexity != "All" else None,
            high_risk_only=high_risk_only,
        )
    except Exception as e:
        st.error(f"Error loading data: {e}")
        df = pd.DataFrame()

# Display results
if df.empty:
    st.info("No messages found matching your filters.")
else:
    st.markdown(f"**Showing {len(df)} messages** (Page {page})")

    for idx, row in df.iterrows():
        # Determine status color
        hallucination = row.get("hallucination_detected", False)
        faithfulness = row.get("faithfulness_score")

        if hallucination:
            status_color = "🔴"
            status_text = "Hallucination"
        elif faithfulness and faithfulness < 0.7:
            status_color = "🟡"
            status_text = "Low Faithfulness"
        else:
            status_color = "🟢"
            status_text = "OK"

        # Create expandable card
        question_preview = str(row.get("question", ""))[:100] + "..." if len(str(row.get("question", ""))) > 100 else str(row.get("question", ""))
        created_at = row.get("created_at", "Unknown time")

        with st.expander(f"{status_color} {question_preview}", expanded=False):
            # Header info
            col_time, col_type, col_risk = st.columns(3)
            with col_time:
                st.caption(f"📅 {created_at}")
            with col_type:
                q_type = row.get("question_type", "N/A")
                q_complexity = row.get("question_complexity", "N/A")
                st.caption(f"Type: {q_type} | Complexity: {q_complexity}")
            with col_risk:
                if row.get("is_high_risk_topic"):
                    st.caption(f"⚠️ High-risk: {row.get('high_risk_category', 'Unknown')}")

            st.markdown("---")

            # Question
            st.markdown("**Question:**")
            st.markdown(f"> {row.get('question', 'N/A')}")

            # Response
            st.markdown("**Response:**")
            response = row.get("response", "N/A")
            st.markdown(response)

            # Sources
            sources = row.get("sources_cited")
            if sources:
                st.markdown("**Sources Cited:**")
                if isinstance(sources, list):
                    for source in sources:
                        if isinstance(source, dict):
                            title = source.get("title", "Unknown")
                            url = source.get("url", "#")
                            st.markdown(f"- [{title}]({url})")
                        else:
                            st.markdown(f"- {source}")
                else:
                    st.text(str(sources))

            st.markdown("---")

            # Evaluation scores
            st.markdown("**Evaluation Scores:**")
            score_col1, score_col2, score_col3, score_col4 = st.columns(4)

            with score_col1:
                faith_score = row.get("faithfulness_score")
                if faith_score is not None:
                    color = "green" if faith_score >= 0.8 else "orange" if faith_score >= 0.6 else "red"
                    st.markdown(f"Faithfulness: :{color}[**{faith_score:.2f}**]")
                else:
                    st.markdown("Faithfulness: N/A")

            with score_col2:
                comp_score = row.get("completeness_score")
                if comp_score is not None:
                    st.markdown(f"Completeness: **{comp_score:.2f}**")
                else:
                    st.markdown("Completeness: N/A")

            with score_col3:
                clarity_score = row.get("clarity_score")
                if clarity_score is not None:
                    st.markdown(f"Clarity: **{clarity_score:.2f}**")
                else:
                    st.markdown("Clarity: N/A")

            with score_col4:
                citation_acc = row.get("citation_accurate")
                if citation_acc is not None:
                    st.markdown(f"Citations Accurate: {'✅' if citation_acc else '❌'}")
                else:
                    st.markdown("Citations: N/A")

            # Hallucination details
            if row.get("hallucination_detected") or row.get("capability_hallucination"):
                st.markdown("---")
                st.markdown("**⚠️ Hallucination Details:**")
                if row.get("hallucination_detected"):
                    st.error("Hallucination detected")
                if row.get("capability_hallucination"):
                    st.error("Capability hallucination (false claim about what the product can do)")

                reasoning = row.get("hallucination_reasoning")
                if reasoning:
                    st.markdown("**Reasoning:**")
                    st.info(reasoning)

            # Faithfulness reasoning
            faith_reasoning = row.get("faithfulness_reasoning")
            if faith_reasoning:
                st.markdown("---")
                st.markdown("**Faithfulness Analysis:**")
                st.info(faith_reasoning)

            # Overall assessment
            assessment = row.get("overall_assessment")
            if assessment:
                st.markdown("---")
                st.markdown("**Overall Assessment:**")
                st.info(assessment)

            # Metadata
            st.markdown("---")
            st.caption(f"Message ID: {row.get('id', 'N/A')} | Response time: {row.get('response_time_ms', 'N/A')}ms | Model: {row.get('model_used', 'N/A')}")
