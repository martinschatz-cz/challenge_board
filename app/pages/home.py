import streamlit as st
import pandas as pd
from db import get_top_results

st.title("🪂 Paragliding Flight Challenges")
st.caption("Welcome to the IGC leaderboard platform. Upload your track logs and compete for top ranks!")

# Active & Upcoming Challenges Grid
st.subheader("🎯 Active Challenges")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info("**📏 Longest Straight Track**\n\nFind the longest straight gliding line within deviation tolerances.")

with col2:
    st.info("**⬆️ Maximum Altitude Gain**\n\nFind the largest continuous altitude gain with no recording gap over 10 seconds.")

with col3:
    st.info("**⭕ Perfect Circle**\n\nFind the longest part of a flight that follows a circular path.")

with col4:
    st.info("**⬇️ Fastest Altitude Loss**\n\nFind the fastest descent measured over 3 seconds.")

st.markdown("---")

# Separate leaderboard for each challenge
straight_tab, circle_tab, altitude_tab, loss_tab = st.tabs([
    "📏 Longest Straight Track",
    "⭕ Perfect Circle",
    "⬆️ Altitude Gain",
    "⬇️ Altitude Loss"
])


def highlight_top3(row):
    if row.name == 0:
        return ['background-color: #ffeaa7; color: #000000; font-weight: bold'] * len(row)
    if row.name == 1:
        return ['background-color: #dfe6e9; color: #000000'] * len(row)
    if row.name == 2:
        return ['background-color: #fab1a0; color: #000000'] * len(row)
    return [''] * len(row)

with straight_tab:
    st.subheader("🏆 Longest Straight Track")
    straight_results = get_top_results(challenge_type="straight_track", limit=7)

    if straight_results:
        straight_df = pd.DataFrame(straight_results)[[
            "Pilot", "Straight Line (m)", "Total Flight (km)",
            "Max Dev (m)", "Start UTC", "End UTC", "Uploaded"
        ]]

        st.dataframe(
            straight_df.style.apply(highlight_top3, axis=1),
            use_container_width=True,
            hide_index=False
        )
    else:
        st.warning("No straight-track entries yet. Be the first to submit a track.")

with circle_tab:
    st.subheader("🏆 Closest Circular Track")
    circle_results = get_top_results(challenge_type="circle_track", limit=7)

    if circle_results:
        circle_df = pd.DataFrame(circle_results).rename(columns={
            "Straight Line (m)": "Circular Arc (m)",
            "Max Dev (m)": "Max Radial Error (m)",
            "Closeness (%)": "Circle Closeness (%)",
            "Circle Radius (m)": "Radius (m)"
        })[[
            "Pilot", "Circular Arc (m)", "Radius (m)",
            "Circle Closeness (%)", "Max Radial Error (m)",
            "Start UTC", "End UTC", "Uploaded"
        ]]
        st.dataframe(
            circle_df.style.apply(highlight_top3, axis=1),
            use_container_width=True,
            hide_index=False
        )
    else:
        st.info("No circular-track entries yet. Upload a flight to detect one.")

with altitude_tab:
    st.subheader("🏆 Maximum Continuous Altitude Gain")
    altitude_results = get_top_results(challenge_type="altitude_gain", limit=7)

    if altitude_results:
        altitude_df = pd.DataFrame(altitude_results)[[
            "Pilot", "Altitude Gain (m)", "Start UTC", "End UTC", "Uploaded"
        ]]
        st.dataframe(
            altitude_df.style.apply(highlight_top3, axis=1),
            use_container_width=True,
            hide_index=False
        )
    else:
        st.info("No altitude-gain entries yet. Upload a flight to create one.")

with loss_tab:
    st.subheader("🏆 Fastest Altitude Loss Over 3 Seconds")
    loss_results = get_top_results(challenge_type="altitude_loss", limit=7)

    if loss_results:
        loss_df = pd.DataFrame(loss_results)[[
            "Pilot", "Altitude Loss Rate (m/s)", "Start UTC", "End UTC", "Uploaded"
        ]]
        st.dataframe(
            loss_df.style.apply(highlight_top3, axis=1),
            use_container_width=True,
            hide_index=False
        )
    else:
        st.info("No altitude-loss entries yet. Upload a flight to create one.")
st.markdown("### Ready to compete?")
if st.button("📤 Upload Your Track Now", type="primary"):
    st.switch_page("pages/upload.py")