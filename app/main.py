import streamlit as st
import pandas as pd
import sqlite3
import folium
from streamlit_folium import st_folium
import os
from igc_parser import analyze_igc_track

st.set_page_config(page_title="IGC Straight Track Competition", layout="wide")

# Database Setup
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "leaderboard.db")

conn = sqlite3.connect(DB_PATH)
conn.execute("""
    CREATE TABLE IF NOT EXISTS leaderboard (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pilot_name TEXT,
        straight_len_m REAL,
        total_len_km REAL,
        max_dev_m REAL,
        start_time TEXT,
        end_time TEXT,
        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

st.title("🪂 Longest Straight Track Leaderboard")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Submit Flight")
    with st.form("flight_form"):
        pilot_name = st.text_input("Pilot / Glider ID", placeholder="e.g. John Doe")
        igc_file = st.file_uploader("Upload IGC Track", type=["igc"])
        max_dev = st.slider("Max Deviation Tolerance (m)", 2, 15, 1)
        submit_btn = st.form_submit_button("Process Track")

    if submit_btn and igc_file and pilot_name:
        temp_path = os.path.join(DATA_DIR, igc_file.name)
        with open(temp_path, "wb") as f:
            f.write(igc_file.getbuffer())

        with st.spinner("Analyzing track geometry..."):
            result = analyze_igc_track(temp_path, max_dev_meters=max_dev)

        if result:
            conn.execute("""
                INSERT INTO leaderboard (pilot_name, straight_len_m, total_len_km, max_dev_m, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pilot_name,
                result['straight_displacement_m'],
                result['total_track_length_km'],
                result['max_dev_m'],
                result['start_time'],
                result['end_time']
            ))
            conn.commit()

            st.success(f"Track added! Longest straight line: {result['straight_displacement_m']} m")
            st.session_state['latest_result'] = result
        else:
            st.error("Could not extract valid flight records from this IGC file.")

with col2:
    st.subheader("🏆 Leaderboard")
    df = pd.read_sql_query("""
        SELECT 
            pilot_name AS 'Pilot', 
            straight_len_m AS 'Straight Line (m)', 
            total_len_km AS 'Total Flight (km)', 
            max_dev_m AS 'Max Dev (m)',
            start_time AS 'Start UTC',
            end_time AS 'End UTC'
        FROM leaderboard 
        ORDER BY straight_len_m DESC
    """, conn)
    
    st.dataframe(df, use_container_width=True, hide_index=True)

# Interactive Map Section
if 'latest_result' in st.session_state:
    res = st.session_state['latest_result']
    st.markdown("---")
    st.subheader("🗺️ Latest Track Visualization")
    
    full_coords = res['full_track_coords']
    straight_coords = res['straight_segment_coords']
    
    if full_coords:
        start_lat, start_lon = full_coords[0]
        m = folium.Map(location=[start_lat, start_lon], zoom_start=12, tiles="OpenStreetMap")
        
        # Plot full flight path (Blue)
        folium.PolyLine(full_coords, color="blue", weight=2, opacity=0.6, popup="Full Track").add_to(m)
        
        # Plot straight segment (Thick Red)
        if straight_coords:
            folium.PolyLine(straight_coords, color="red", weight=5, opacity=0.9, popup="Longest Straight Track").add_to(m)
            
            # Start/End Markers
            folium.Marker(straight_coords[0], popup=f"Start Straight: {res['start_time']}", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(straight_coords[-1], popup=f"End Straight: {res['end_time']}", icon=folium.Icon(color="red")).add_to(m)
        
        st_folium(m, width=1200, height=500)