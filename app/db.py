import sqlite3
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "leaderboard.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        # 1. Base Table Creation
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pilot_name TEXT NOT NULL,
                straight_len_m REAL,
                total_len_km REAL,
                max_dev_m REAL,
                closeness_pct REAL,
                circle_radius_m REAL,
                altitude_gain_m REAL,
                altitude_loss_rate_mps REAL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Auto-Migrate missing columns if table already existed from earlier builds
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(leaderboard)")
        existing_columns = [column[1] for column in cursor.fetchall()]

        if "challenge_type" not in existing_columns:
            conn.execute("ALTER TABLE leaderboard ADD COLUMN challenge_type TEXT DEFAULT 'straight_track'")
        if "start_time" not in existing_columns:
            conn.execute("ALTER TABLE leaderboard ADD COLUMN start_time TEXT")
        if "end_time" not in existing_columns:
            conn.execute("ALTER TABLE leaderboard ADD COLUMN end_time TEXT")
        if "closeness_pct" not in existing_columns:
            conn.execute("ALTER TABLE leaderboard ADD COLUMN closeness_pct REAL")
        if "circle_radius_m" not in existing_columns:
            conn.execute("ALTER TABLE leaderboard ADD COLUMN circle_radius_m REAL")
        if "altitude_gain_m" not in existing_columns:
            conn.execute("ALTER TABLE leaderboard ADD COLUMN altitude_gain_m REAL")
        if "altitude_loss_rate_mps" not in existing_columns:
            conn.execute("ALTER TABLE leaderboard ADD COLUMN altitude_loss_rate_mps REAL")
            
        conn.commit()

def save_submission(
    pilot_name, straight_m, total_km, max_dev, start_t, end_t,
    challenge_type="straight_track", closeness_pct=None, circle_radius_m=None,
    altitude_gain_m=None, altitude_loss_rate_mps=None
):
    init_db()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO leaderboard 
            (pilot_name, challenge_type, straight_len_m, total_len_km, max_dev_m,
                 closeness_pct, circle_radius_m, altitude_gain_m,
                 altitude_loss_rate_mps, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pilot_name, challenge_type, straight_m, total_km, max_dev,
                    closeness_pct, circle_radius_m, altitude_gain_m,
                    altitude_loss_rate_mps, start_t, end_t))
        conn.commit()

def get_top_results(challenge_type="straight_track", limit=7):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                pilot_name AS 'Pilot', 
                straight_len_m AS 'Straight Line (m)', 
                total_len_km AS 'Total Flight (km)', 
                max_dev_m AS 'Max Dev (m)',
                closeness_pct AS 'Closeness (%)',
                circle_radius_m AS 'Circle Radius (m)',
                altitude_gain_m AS 'Altitude Gain (m)',
                altitude_loss_rate_mps AS 'Altitude Loss Rate (m/s)',
                start_time AS 'Start UTC',
                end_time AS 'End UTC',
                upload_date AS 'Uploaded'
            FROM leaderboard 
            WHERE challenge_type = ?
            ORDER BY CASE
                WHEN challenge_type = 'circle_track' THEN closeness_pct
                WHEN challenge_type = 'altitude_gain' THEN altitude_gain_m
                WHEN challenge_type = 'altitude_loss' THEN altitude_loss_rate_mps
                ELSE straight_len_m
            END DESC,
            CASE
                WHEN challenge_type = 'circle_track' THEN straight_len_m
                ELSE 0
            END DESC
            LIMIT ?
        """, (challenge_type, limit))
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]