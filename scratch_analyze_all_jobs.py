import sqlite3
import json
from app.services.pdf_export_service import (
    get_valid_projects,
    compute_layout,
    estimate_height_pt,
    USABLE_HEIGHT_PT,
    CHARS_PER_LINE,
    flatten_bullets,
    strip_bold,
    sanitize_bullet
)

conn = sqlite3.connect('resume_analyzer.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT id, candidate_name, status, result_json FROM cv_jobs WHERE status="COMPLETED"')
jobs = cur.fetchall()

print(f"Total completed jobs: {len(jobs)}")
for j in jobs:
    print(f"\n========================================================")
    print(f"JOB ID: {j['id']} | Candidate: {j['candidate_name']}")
    print(f"========================================================")
    data = json.loads(j['result_json'])
    summary = data.get('professional_summary', '')
    raw_projects = data.get('major_project_experience', [])
    
    print(f"Professional Summary words: {len(summary.split())}, chars: {len(summary)}")
    print(f"Total raw projects in LLM response: {len(raw_projects)}")
    
    valid_projects = get_valid_projects(raw_projects)
    print(f"Valid projects: {len(valid_projects)}")
    
    for i, p in enumerate(valid_projects):
        raw_buls = p.get('bullets', [])
        flat_buls = flatten_bullets(raw_buls)
        print(f"  Project {i+1}: {p.get('project_title')}")
        print(f"    Role: {p.get('role')}")
        print(f"    Raw bullets from LLM: {len(raw_buls)}, Valid flat bullets: {len(flat_buls)}")
        for bi, b in enumerate(flat_buls):
            safe_b = b[:75].encode('ascii', errors='replace').decode('ascii')
            print(f"      b{bi+1} ({len(b)} chars): {safe_b}...")
            
    layout = compute_layout(summary, valid_projects)
    bpp_list = layout["bullets_per_project_list"]
    print(f"\nLayout Calculation Result:")
    print(f"  Bullets allowed per project: {bpp_list} (Total bullets rendered = {sum(bpp_list)} out of {sum(len(flatten_bullets(p.get('bullets',[]))) for p in valid_projects)} generated)")
    print(f"  Fonts: Title={layout['title_font_pt']}pt, Body={layout['body_font_pt']}pt")
    
    # Calculate height breakdown
    sum_lines = len(summary) / 68.0
    print(f"  Estimated lines for summary (with chars_per_line=68): {sum_lines:.1f} lines")
    print(f"  Actual lines for summary on 7.5\" wide slide (~125 chars/line): {len(summary)/125.0:.1f} lines")

conn.close()
