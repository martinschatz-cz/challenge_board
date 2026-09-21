import sqlite3
import os

DATA_DIR = "data"
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
            
        conn.commit()

def save_submission(pilot_name, straight_m, total_km, max_dev, start_t, end_t, challenge_type="straight_track"):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO leaderboard 
            (pilot_name, challenge_type, straight_len_m, total_len_km, max_dev_m, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (pilot_name, challenge_type, straight_m, total_km, max_dev, start_t, end_t))
        conn.commit()

def get_top_results(challenge_type="straight_track", limit=7):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                pilot_name AS 'Pilot', 
                straight_len_m AS 'Straight Line (m)', 
                total_len_km AS 'Total Flight (km)', 
                max_dev_m AS 'Max Dev (m)',
                start_time AS 'Start UTC',
                end_time AS 'End UTC',
                upload_date AS 'Uploaded'
            FROM leaderboard 
            WHERE challenge_type = ?
            ORDER BY straight_len_m DESC
            LIMIT ?
        """, (challenge_type, limit))
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]