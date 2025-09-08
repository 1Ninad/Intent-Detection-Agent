import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Intent Detection Web Search", layout="wide")

st.title("Intent Detection Web Search")

# Input area for the salesperson's free-text
free_text = st.text_area("Enter your search or requirements", height=150)

# Option to use web search
use_web_search = st.checkbox("Use Web Search", value=True)

# Button to trigger the search
if st.button("Search"):
    if not free_text.strip():
        st.error("Please enter some text to search.")
    else:
        with st.spinner("Searching..."):
            url = "http://localhost:8000/run"  # FastAPI endpoint
            payload = {
                "freeText": free_text,
                "useWebSearch": use_web_search
            }
            try:
                response = requests.post(url, json=payload)
                response.raise_for_status()  # Raise error for bad responses
                data = response.json()

                web_signals = data.get("webSignals", [])

                if web_signals:
                    st.success(f"Found {len(web_signals)} signals!")
                    df = pd.DataFrame(web_signals)
                    st.dataframe(df)
                else:
                    st.warning("No signals found.")

            except requests.exceptions.RequestException as e:
                st.error(f"Error calling API: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
