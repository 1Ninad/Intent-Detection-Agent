import streamlit as st
import pandas as pd
import json

st.title("Prospect Ranking Dashboard")

# --- Step 1: Load teammate JSON files ---
try:
    with open("ui/classification.json", "r") as f:
        classify_data = json.load(f)
except:
    classify_data = []
    st.warning("classification.json not found")

try:
    with open("ui/ranking.json", "r") as f:
        rank_data = json.load(f)
except:
    rank_data = []
    st.warning("ranking.json not found")

# Merge results
data = classify_data + rank_data

# Fallback if no data
if not data:
    data = [
        {"Company": "Demo Corp", "fitScore": 0.80, "preferenceIndicator": 0.70,
         "signals": ["Funding Round"], "evidence": ["https://news.site/demo"],
         "reason": "Demo data for testing"}
    ]

# --- Step 2: Show table ---
df = pd.DataFrame(data)
st.dataframe(df)

# --- Step 3: Drill-down view ---
company = st.selectbox("Select a company:", df["Company"])
if company:
    details = df[df["Company"] == company].iloc[0]
    st.subheader(f"Details for {company}")
    st.write("Fit Score:", details.get("fitScore", "N/A"))
    st.write("Preference Indicator:", details.get("preferenceIndicator", "N/A"))
    st.write("Signals:", details.get("signals", []))
    st.write("Evidence URLs:")
    for url in details.get("evidence", []):
        st.write(f"- [{url}]({url})")
    st.write("Reason:", details.get("reason", "N/A"))
