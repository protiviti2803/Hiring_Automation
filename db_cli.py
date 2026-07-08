import sys
import argparse
from app.core.database import get_db_connection
from app.services.db_service import get_demand_and_jd_by_id

def list_records():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, demands, created_at FROM client_demands ORDER BY id DESC")
        rows = cursor.fetchall()
        if not rows:
            print("No records found in the database.")
            return
        print(f"{'ID':<5} | {'Created At':<20} | {'Client Demand (preview)':<50}")
        print("-" * 80)
        for row in rows:
            # Clean newlines from preview
            demand_clean = row["demands"].replace("\n", " ").strip()
            demand_preview = demand_clean[:47] + "..." if len(demand_clean) > 50 else demand_clean
            print(f"{row['id']:<5} | {row['created_at']:<20} | {demand_preview:<50}")
    finally:
        conn.close()

def view_record(record_id):
    record = get_demand_and_jd_by_id(record_id)
    if not record:
        print(f"Error: Record with ID {record_id} not found.")
        return
    print("=" * 60)
    print(f"Record ID: {record_id}")
    print("=" * 60)
    print(f"DEMAND:\n{record['demand']}\n")
    print("-" * 60)
    print(f"GENERATED JD:\n{record['JD']}\n")
    print("-" * 60)
    print(f"KEYWORDS: {', '.join(record['keywords'])}")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resume Analyzer DB CLI Utility")
    parser.add_argument("--list", action="store_true", help="List all stored records")
    parser.add_argument("--view", type=int, help="View a specific record by ID")
    
    args = parser.parse_args()
    if args.list:
        list_records()
    elif args.view is not None:
        view_record(args.view)
    else:
        parser.print_help()
