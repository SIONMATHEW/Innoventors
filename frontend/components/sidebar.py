import requests
import streamlit as st

def _health(api_url: str) -> bool:
    try:
        r = requests.get(f"{api_url}/health", timeout=6)
        return r.ok
    except Exception:
        return False

def sidebar_controls(api_url: str):
    st.sidebar.markdown("## 🧩 Controls")

    healthy = _health(api_url)
    st.sidebar.metric("Backend", "Online ✅" if healthy else "Offline ❌")

    st.sidebar.divider()

    with st.sidebar.expander("Settings", expanded=True):
        st.write("Backend URL")
        _ = st.text_input(
            "INNOVENTORS_API_URL (read-only here, set via env)",
            value=api_url,
            disabled=True,
            label_visibility="collapsed"
        )

        st.caption("Tip: Set `INNOVENTORS_API_URL` env var in production.")

    st.sidebar.divider()

    if st.sidebar.button("🧹 Reset Database", use_container_width=True):
        with st.spinner("Resetting database…"):
            try:
                res = requests.delete(f"{api_url}/reset", timeout=20)
                if res.status_code == 200:
                    # Clear all cached data globally & rerun
                    st.cache_data.clear()
                    st.sidebar.success("Database cleared.")
                    st.rerun()
                else:
                    st.sidebar.error("Reset failed.")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

    st.sidebar.divider()
    st.sidebar.caption("Use Reset sparingly if you want a clean demo state.")
