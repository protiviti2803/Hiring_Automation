import sqlite3
import os

# Set the database path to 'resume_analyzer.db' in the root directory
# Since app/core/database.py is located at app/core/database.py,
# the root directory is three directories up.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "resume_analyzer.db")

def get_db_connection():
    """Returns an active SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the client_demands table if it doesn't exist."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_demands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                demands TEXT NOT NULL,
                generated_JD TEXT NOT NULL,
                keywords TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
