import sqlite3
import json
from app.core.database import get_db_connection

def init_jobs_db():
    """Initializes the cv_jobs table if it does not exist, enforcing schema upgrades dynamically."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if table exists and has the match_score column
        cursor.execute("PRAGMA table_info(cv_jobs)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and "match_score" not in columns:
            print("[DB] Upgrading schema: dropping old cv_jobs table to add match_score/match_reason/jd_text columns.")
            cursor.execute("DROP TABLE cv_jobs")
            
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cv_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_name TEXT,
                email TEXT UNIQUE,
                raw_text TEXT,
                jd_text TEXT,
                match_score INTEGER DEFAULT 0,
                match_reason TEXT,
                status TEXT CHECK(status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')) DEFAULT 'PENDING',
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        # Reset any orphaned stuck jobs from previous run back to PENDING
        reset_orphaned_jobs()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_job(candidate_name: str | None, email: str, raw_text: str, jd_text: str = "") -> int:
    """Creates or updates a CV standardization job (UPSERT on email) and returns the job ID."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO cv_jobs (candidate_name, email, raw_text, jd_text, status, updated_at)
            VALUES (?, ?, ?, ?, 'PENDING', CURRENT_TIMESTAMP)
            ON CONFLICT(email)
            DO UPDATE SET
                candidate_name = excluded.candidate_name,
                raw_text = excluded.raw_text,
                jd_text = excluded.jd_text,
                status = 'PENDING',
                updated_at = CURRENT_TIMESTAMP
            """,
            (candidate_name, email, raw_text, jd_text)
        )
        conn.commit()
        
        row_id = cursor.lastrowid
        if not row_id:
            cursor.execute("SELECT id FROM cv_jobs WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row:
                row_id = row[0]
        return row_id
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_all_jobs() -> list:
    """Returns a list of all jobs in the database (id, candidate_name, status, match_score, match_reason, created_at)."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, candidate_name, status, match_score, match_reason, created_at FROM cv_jobs ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_job_by_id(job_id: int) -> dict | None:
    """Returns the detailed record of a single job."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM cv_jobs WHERE id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_job_result(job_id: int, result_json: str, match_score: int = 0, match_reason: str | None = None) -> bool:
    """Updates the result_json, match_score, and match_reason for a job and marks it as COMPLETED."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE cv_jobs 
            SET result_json = ?, match_score = ?, match_reason = ?, status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
            """,
            (result_json, match_score, match_reason, job_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_job_status(job_id: int, status: str, error_message: str | None = None, retry_count: int | None = None) -> bool:
    """Updates status, error_message, and optionally retry_count of a job."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if retry_count is not None:
            cursor.execute(
                "UPDATE cv_jobs SET status = ?, error_message = ?, retry_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, error_message, retry_count, job_id)
            )
        else:
            cursor.execute(
                "UPDATE cv_jobs SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, error_message, job_id)
            )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def claim_next_job() -> dict | None:
    """
    Safely retrieves and claims the oldest PENDING job using standard SQLite transaction locking.
    Uses 'BEGIN IMMEDIATE' to block write conflicts and simulate SKIP LOCKED behavior.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        # BEGIN IMMEDIATE locks the database for writing immediately, preventing race conditions
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()
        
        # Select the oldest PENDING job with less than 3 retries
        cursor.execute("""
            SELECT id, candidate_name, raw_text, jd_text, retry_count 
            FROM cv_jobs 
            WHERE status = 'PENDING' AND retry_count < 3 
            ORDER BY id ASC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        
        if row:
            job_id = row["id"]
            new_retry_count = row["retry_count"] + 1
            # Update the job to PROCESSING state immediately
            cursor.execute("""
                UPDATE cv_jobs 
                SET status = 'PROCESSING', retry_count = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (new_retry_count, job_id))
            conn.commit()
            return {
                "id": job_id,
                "candidate_name": row["candidate_name"],
                "raw_text": row["raw_text"],
                "jd_text": row["jd_text"],
                "retry_count": new_retry_count
            }
        else:
            # If no job is found, release the transaction
            conn.commit()
            return None
    except sqlite3.OperationalError as e:
        # SQLite busy/locked exceptions are expected under load; roll back and retry later
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"Database locked or busy during claim_next_job: {e}")
        return None
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"Error claiming next job: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def reset_orphaned_jobs():
    """Resets jobs stuck in 'PROCESSING' state back to 'PENDING' on startup/recovery."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cv_jobs SET status = 'PENDING' WHERE status = 'PROCESSING'"
        )
        conn.commit()
        print("[DB] Safely reset orphaned PROCESSING jobs back to PENDING.")
    except Exception as e:
        print(f"Failed to reset orphaned jobs: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def delete_job_by_id(job_id: int) -> bool:
    """Deletes a single job from the database by its ID."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cv_jobs WHERE id = ?", (job_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Failed to delete job {job_id}: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
