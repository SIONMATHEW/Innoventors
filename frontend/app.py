import os
import streamlit as st

# Import components
from components.sidebar import sidebar_controls
from components.upload_section import upload_section
from components.dashboard import show_dashboard

st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)

# -----------------------------------------
# Page config
# -----------------------------------------
st.set_page_config(
    page_title="Innoventors – AI Incident Intelligence",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------
# Config / constants
# -----------------------------------------
API_URL = os.getenv("INNOVENTORS_API_URL", "http://127.0.0.1:8000")
ASSETS_DIR = os.path.join("frontend", "assets")

# -----------------------------------------
# Global CSS
# -----------------------------------------
css_path = os.path.join(ASSETS_DIR, "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# -----------------------------------------
# Sidebar Controls (health, reset, info)
# -----------------------------------------
sidebar_controls(API_URL)

# -----------------------------------------
# Header
# -----------------------------------------
st.markdown("""
<div class="page-title">
  <div>
    <h2>🚀 Innoventors</h2>
    <p>AI-Driven Incident Intelligence • Upload scenarios, generate RCA, and explore insights</p>
  </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------
# Upload & Analyze
# -----------------------------------------
upload_section(API_URL)

# -----------------------------------------
# Dashboard (incidents + analytics)
# -----------------------------------------
show_dashboard(API_URL)

# Footer
st.caption("© Innoventors • A+ clean code • PSA CodeSprint 2025")
