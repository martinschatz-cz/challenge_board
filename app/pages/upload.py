import streamlit as st
import os
import folium
from streamlit_folium import st_folium
from igc_parser import analyze_igc_track
from db import save_submission

st.title("📤 Submit Your Flight Track")

DATA_DIR = "data"

with st.form("upload_form"):
    pilot_name = st.text_input("Pilot / Glider ID", placeholder="e.g. John Doe")
    igc_file = st.file_uploader("Upload IGC Track (Max 50 MB)", type=["igc"])
    
    max_dev = st.slider("Straight-line deviation tolerance (m)", 2, 15, 5)
    
    submitted = st.form_submit_button("Submit Track", type="primary")

if submitted:
    if not pilot_name:
        st.error("Please enter your name or Glider ID.")
    elif not igc_file:
        st.error("Please select an IGC file to upload.")
    else:
        temp_path = os.path.join(DATA_DIR, igc_file.name)
        with open(temp_path, "wb") as f:
            f.write(igc_file.getbuffer())

        with st.spinner("Processing track geometry..."):
            result = analyze_igc_track(
                temp_path,
                max_dev_meters=max_dev
            )

        if result:
            save_submission(
                pilot_name=pilot_name,
                straight_m=result['straight_displacement_m'],
                total_km=result['total_track_length_km'],
                max_dev=result['max_dev_m'],
                start_t=result['start_time'],
                end_t=result['end_time'],
                challenge_type="straight_track"
            )

            st.balloons()
            st.success(
                f"Track processed! Longest straight segment: **{result['straight_displacement_m']} meters**"
            )
            
            # Show Map preview
            full_coords = result['full_track_coords']
            straight_coords = result['straight_segment_coords']
            
            if full_coords:
                m = folium.Map(location=full_coords[0], zoom_start=12)
                folium.PolyLine(full_coords, color="blue", weight=2, opacity=0.5, popup="Full Flight").add_to(m)
                if straight_coords:
                    folium.PolyLine(straight_coords, color="red", weight=5, opacity=0.9, popup="Straight Segment").add_to(m)
                st_folium(m, width=1000, height=400)
                
            if st.button("🏆 View Leaderboard"):
                st.switch_page("pages/home.py")
        else:
            st.error("Could not parse valid B-records from this IGC file.")