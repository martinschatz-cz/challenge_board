import streamlit as st
import pandas as pd
from db import get_top_results

st.title("🪂 Paragliding Flight Challenges")
st.caption("Welcome to the IGC leaderboard platform. Upload your track logs and compete for top ranks!")

# Active & Upcoming Challenges Grid
st.subheader("🎯 Active Challenges")
col1, col2, col3 = st.columns(3)

with col1:
    st.info("**📏 Longest Straight Track**\n\nFind the longest straight gliding line within deviation tolerances.")

with col2:
    st.markdown("```\n🔒 Coming Soon: Max Altitude Gain\n```")

with col3:
    st.info("**⭕ Perfect Circle**\n\nFind the longest part of a flight that follows a circular path.")

st.markdown("---")

# Leaderboard Section
st.subheader("🏆 Top 7 Leaderboard - Longest Straight Track")

top_7 = get_top_results(challenge_type="straight_track", limit=7)

if top_7:
    df = pd.DataFrame(top_7)
    
    # Highlight top 3 podium
    def highlight_top3(row):
        if row.name == 0:
            return ['background-color: #ffeaa7; font-weight: bold'] * len(row) # 🥇 Gold
        elif row.name == 1:
            return ['background-color: #dfe6e9'] * len(row) # 🥈 Silver
        elif row.name == 2:
            return ['background-color: #fab1a0'] * len(row) # 🥉 Bronze
        return [''] * len(row)

    st.dataframe(
        df.style.apply(highlight_top3, axis=1),
        use_container_width=True,
        hide_index=False
    )
else:
    st.warning("No entries yet! Be the first to submit a track.")

st.subheader("⭕ Top 7 Leaderboard - Closest Circular Track")
circle_results = get_top_results(challenge_type="circle_track", limit=7)

if circle_results:
    st.dataframe(
        pd.DataFrame(circle_results).rename(columns={
            "Straight Line (m)": "Circular Arc (m)",
            "Max Dev (m)": "Max Radial Error (m)"
        }),
        use_container_width=True,
        hide_index=False
    )
else:
    st.info("No circular track entries yet. Upload a flight to detect one.")

st.markdown("### Ready to compete?")
if st.button("📤 Upload Your Track Now", type="primary"):
    st.switch_page("pages/upload.py")