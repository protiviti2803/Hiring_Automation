import sqlite3
import os

# Set the database path to 'resume_analyzer.db' in the root directory
# Since app/core/database.py is located at app/core/database.py,
# the root directory is three directories up.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "resume_analyzer.db")

def get_db_connection():
    """Returns an active SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates all tables if they don't exist."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create client_demands
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_demands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                demands TEXT NOT NULL,
                generated_JD TEXT NOT NULL,
                keywords TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create candidates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                name TEXT,
                email TEXT,
                resume_text TEXT,
                status TEXT,
                resume_score INTEGER,
                reasoning TEXT
            )
        """)
        
        # Create interview_sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interview_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                total_candidates INTEGER,
                completed_candidates INTEGER,
                status TEXT
            )
        """)
        
        # Create session_questions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                candidate_id INTEGER,
                raw_text TEXT,
                standardized_question TEXT,
                category TEXT
            )
        """)
        
        # Drop legacy master_questions if it contains the old column naming structure
        cursor.execute("PRAGMA table_info(master_questions)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if existing_cols and "frequency_count" in existing_cols:
            cursor.execute("DROP TABLE master_questions")
        
        # Create master_questions with unique constraint on question_text and check constraint on type
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS master_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT UNIQUE,
                frequency INTEGER DEFAULT 1,
                type TEXT CHECK(type IN ('GENERIC', 'DOMAIN'))
            )
        """)

        # Create client_feedbacks (post-interview feedback + categorized keywords)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_demand TEXT,
                raw_feedback TEXT NOT NULL,
                candidate_name TEXT DEFAULT '',
                role TEXT DEFAULT '',
                hard_skills TEXT DEFAULT '[]',
                soft_skills TEXT DEFAULT '[]',
                domain_knowledge TEXT DEFAULT '[]',
                behavioral_knowledge TEXT DEFAULT '[]',
                reasoning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: add candidate_name / role columns to pre-existing tables
        cursor.execute("PRAGMA table_info(client_feedbacks)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if "candidate_name" not in existing_cols:
            cursor.execute("ALTER TABLE client_feedbacks ADD COLUMN candidate_name TEXT DEFAULT ''")
        if "role" not in existing_cols:
            cursor.execute("ALTER TABLE client_feedbacks ADD COLUMN role TEXT DEFAULT ''")

        conn.commit()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

