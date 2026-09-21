import streamlit as st
from db import init_db

st.set_page_config(page_title="IGC Flight Challenges", layout="wide", page_icon="🪂")

# Initialize SQLite tables on startup
init_db()

# Multi-page setup
home_page = st.Page("pages/home.py", title="Challenges & Leaderboards", icon="🏆", default=True)
upload_page = st.Page("pages/upload.py", title="Upload Track", icon="📤")

pg = st.navigation({
    "Navigation": [home_page, upload_page]
})

pg.run()