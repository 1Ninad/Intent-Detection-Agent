import streamlit as st
import pandas as pd
import requests

st.title("Prospect Ranking Dashboard")

user_input = st.text_input("Enter search query")

if st.button("Search"):
    API_URL = "http://localhost:8000/run"
    try:
        response = requests.post(API_URL, json={"freeText": user_input, "useWebSearch": True})
        data = response.json()
        df = pd.DataFrame(data["webSignals"])
        st.dataframe(df)
    except Exception as e:
        st.error(f"API call failed: {e}")
