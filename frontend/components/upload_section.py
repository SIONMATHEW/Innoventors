import requests
import streamlit as st

def _analyze_pdf(api_url: str, file) -> dict:
    files = {
        "file": (file.name, file.getvalue(), file.type or "application/octet-stream")
    }
    r = requests.post(f"{api_url}/analyze", files=files, timeout=180)
    r.raise_for_status()
    return r.json()

def upload_section(api_url: str):
    st.markdown("### 1) Upload & Analyze")
    st.write("Drop your **Test Cases PDF** (or TXT). The app detects each *Test Case/Scenario* and generates a structured Root Cause Analysis.")

    c1, c2 = st.columns([0.72, 0.28], vertical_alignment="center")
    with c1:
        uploaded = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"], label_visibility="collapsed")
    with c2:
        analyze = st.button("🔎 Analyze", use_container_width=True, type="primary")

    if analyze:
        if uploaded is None:
            st.warning("Please select a file first.")
            return
        with st.spinner("Analyzing incidents… ⏳"):
            try:
                result = _analyze_pdf(api_url, uploaded)
                total = result.get("total_incidents", 0)
                fname = result.get("file", {}).get("filename") or uploaded.name
                st.success(f"✅ {total} incident(s) analyzed from **{fname}**")
                # bust caches and refresh the page
                st.cache_data.clear()
                st.rerun()
            except requests.HTTPError as e:
                detail = None
                try:
                    detail = e.response.json()
                except Exception:
                    detail = e.response.text if e.response is not None else str(e)
                st.error(f"Server error: {detail}")
            except Exception as e:
                st.error(f"Analysis failed: {e}")
