import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="B2B Intent Detection Agent", layout="wide", page_icon="🎯")

# Header
st.title("🎯 B2B Intent Detection Agent")
st.markdown("**Find prospect companies showing buying intent based on web signals**")

# Instructions
with st.expander("📋 How to use this tool"):
    st.markdown("""
    1. Describe your company and what you sell
    2. Describe your ideal customer profile (industry, signals, etc.)
    3. Click "Find Prospects"
    4. Review ranked companies with evidence

    **Example Input:**
    > We provide AI-driven analytics platforms for healthcare providers.
    > Find hospitals and healthcare companies that recently announced AI partnerships,
    > technology investments, or are hiring data scientists.
    """)

# Input Section
st.markdown("---")
st.subheader("1️⃣ Tell us about your company")

free_text = st.text_area(
    label="Describe your company and ideal prospects:",
    height=150,
    placeholder="Example: We provide cloud infrastructure software for fintech companies. Looking for companies raising funding or migrating to cloud...",
    help="Be specific about your product, target industry, and what signals indicate buying intent"
)

# Advanced options
with st.expander("⚙️ Advanced Options"):
    col1, col2 = st.columns(2)
    with col1:
        top_k = st.slider("Number of prospects to find", min_value=3, max_value=20, value=8, step=1)
        recency = st.selectbox("Recency filter", ["month", "week", "year"], index=0)
    with col2:
        use_web_search = st.checkbox("Enable web search", value=True, help="Use Perplexity AI to find latest signals")
        model = st.selectbox("Search model", ["sonar-pro", "sonar"], index=0)

# Search Button
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    search_button = st.button("🔍 Find Prospects", use_container_width=True, type="primary")

# Results Section
if search_button:
    if not free_text.strip():
        st.error("⚠️ Please enter a description of your company and ideal prospects.")
    else:
        with st.spinner("🔄 Searching for prospects... This may take 30-60 seconds..."):
            url = "http://localhost:8004/run"
            payload = {
                "freeText": free_text,
                "useWebSearch": use_web_search,
                "topK": top_k,
                "webSearchOptions": {
                    "recency": recency,
                    "model": model
                }
            }

            try:
                response = requests.post(url, json=payload, timeout=120)
                response.raise_for_status()
                data = response.json()

                # Extract results
                results = data.get("results", [])
                processed_companies = data.get("processedCompanies", 0)
                labeled_signals = data.get("labeledSignals", 0)
                debug_info = data.get("debug", {})

                if not results:
                    st.warning("🤷 No prospects found matching your criteria. Try broadening your search.")
                else:
                    st.success(f"✅ Found {len(results)} prospect companies!")

                    # Stats
                    st.markdown("---")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Companies Found", processed_companies)
                    with col2:
                        st.metric("Signals Analyzed", labeled_signals)
                    with col3:
                        st.metric("Web Signals", debug_info.get("webSignalsCount", 0))
                    with col4:
                        ingest_stats = debug_info.get("ingestStats", {})
                        st.metric("Embeddings", ingest_stats.get("embeddings", 0))

                    st.markdown("---")
                    st.subheader("🏆 Ranked Prospects")

                    # Display each prospect
                    for idx, prospect in enumerate(results, 1):
                        company_id = prospect.get("companyId", "Unknown")
                        fit_score = prospect.get("fitScore", 0)
                        reasons = prospect.get("reasons", [])

                        # Score color
                        if fit_score >= 0.7:
                            score_color = "🟢"
                        elif fit_score >= 0.4:
                            score_color = "🟡"
                        else:
                            score_color = "🔴"

                        # Company card
                        with st.container():
                            col1, col2 = st.columns([3, 1])

                            with col1:
                                st.markdown(f"### {idx}. {company_id}")

                            with col2:
                                st.markdown(f"**Fit Score:** {score_color} **{fit_score:.2f}**")

                            # Reasons
                            if reasons:
                                st.markdown("**Why this company:**")
                                reason_cols = st.columns(len(reasons))
                                for i, reason in enumerate(reasons):
                                    with reason_cols[i]:
                                        st.info(f"📊 {reason}")

                            # Get signal details from Neo4j (if available)
                            st.markdown("---")

                    # Additional info from debug
                    with st.expander("🔍 View Raw Data"):
                        st.json(data)

                    # Download option
                    st.markdown("---")
                    df = pd.DataFrame(results)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results (CSV)",
                        data=csv,
                        file_name="prospects.csv",
                        mime="text/csv",
                    )

            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. The search is taking longer than expected. Please try again with fewer prospects or broader criteria.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 Cannot connect to the backend service. Make sure the orchestrator is running on http://localhost:8004")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error calling API: {e}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
                import traceback
                with st.expander("Show error details"):
                    st.code(traceback.format_exc())

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>🤖 Powered by Perplexity AI, Neo4j, Qdrant & OpenAI</p>
    <p style='font-size: 12px;'>Intent Detection Agent v1.0</p>
</div>
""", unsafe_allow_html=True)