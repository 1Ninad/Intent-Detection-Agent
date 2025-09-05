import os
import json
import requests
import streamlit as st

API_BASE = os.getenv("ORCH_API_BASE", "http://localhost:8004")

st.set_page_config(page_title="Customer Discovery", layout="wide")
st.title("Customer Discovery")

userText = st.text_area(
    "Describe your ICP/targets/filters in your own words",
    placeholder='e.g. "Find SaaS companies in Europe that raised Series A last month and are hiring data engineers."',
    height=160,
)

runClicked = st.button("Run Search")

def callOrchestrator(free_text: str) -> dict:
    url = f"{API_BASE}/run"
    payload = {
        "freeText": free_text,
        "useWebSearch": True
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    # Raise for non-2xx responses to surface precise errors
    resp.raise_for_status()
    return resp.json()

if runClicked:
    free_text = (userText or "").strip()
    if not free_text:
        st.error("Please enter a description.")
    else:
        with st.spinner("Running orchestrator..."):
            try:
                data = callOrchestrator(free_text)
                st.success("Completed")

                # Show raw response for now (table rendering comes in later steps)
                with st.expander("Raw response"):
                    st.code(json.dumps(data, indent=2))
            except requests.exceptions.HTTPError as e:
                # Show backend-provided message if any
                try:
                    err_json = e.response.json()
                    st.error(f"HTTP {e.response.status_code}: {json.dumps(err_json, indent=2)}")
                except Exception:
                    st.error(f"HTTP {e.response.status_code}: {e.response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Network error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")