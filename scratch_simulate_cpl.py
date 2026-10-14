import sqlite3
import json
import math

from app.services.pdf_export_service import (
    get_valid_projects,
    flatten_bullets,
    strip_bold,
    sanitize_bullet
)

def lines_calc(text: str, cpl: int) -> int:
    text = text.strip()
    if not text:
        return 0
    return max(1, math.ceil(len(text) / cpl))

def est_h(summary: str, projects: list, bpp_list: list, cpl: int,
          title_sp=11.0, body_sp=10.5, sp_before=4.0, sp_after_b=1.5, sum_sp=11.0):
    total = 14.0 # Header
    total += lines_calc(strip_bold(sanitize_bullet(summary)), cpl) * sum_sp + 2.0
    total += 12.0 + 11.0 + 4.0 # Major projects header
    
    for i, proj in enumerate(projects):
        raw_title = strip_bold(proj.get('project_title') or proj.get('title') or '')
        title_cpl = max(1, int(cpl * 8.0 / 8.5))
        total += sp_before + lines_calc(raw_title, title_cpl) * title_sp + 1.0
        bpp = bpp_list[i] if i < len(bpp_list) else 3
        bullets = flatten_bullets(proj.get('bullets', []))
        for b in bullets[:bpp]:
            total += lines_calc(b, cpl) * body_sp + sp_after_b
    return total

conn = sqlite3.connect('resume_analyzer.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT id, candidate_name, result_json FROM cv_jobs WHERE status="COMPLETED"')
jobs = cur.fetchall()

USABLE_HEIGHT_PT = 486.0 # Slide height is 7.5" = 540pt. Placeholder is 6.23" = 448.5pt

for j in jobs:
    data = json.loads(j['result_json'])
    summary = data.get('professional_summary', '')
    raw_projects = data.get('major_project_experience', [])
    projects = get_valid_projects(raw_projects)
    n = len(projects)
    if n <= 3: ideal_bpp = 5
    elif n <= 5: ideal_bpp = 4
    else: ideal_bpp = 3
    
    cand_name = j['candidate_name'].encode('ascii', errors='replace').decode('ascii')
    print(f"\n=======================================================")
    print(f"Candidate: {cand_name} (Projects: {n}, Ideal BPP: {ideal_bpp})")
    print(f"=======================================================")
    
    # Test for various CPL values
    for cpl in [68, 85, 100, 115, 125, 135]:
        current_bpp = [min(ideal_bpp, max(1, len(flatten_bullets(p.get('bullets', []))))) for p in projects]
        
        # Run reduction loop
        for _ in range(60):
            if est_h(summary, projects, current_bpp, cpl) <= USABLE_HEIGHT_PT * 0.995:
                break
            reducible = [(i, b) for i, b in enumerate(current_bpp) if b > 1]
            if not reducible:
                break
            idx_reduce = max(reducible, key=lambda x: x[1])[0]
            current_bpp[idx_reduce] -= 1
            
        h = est_h(summary, projects, current_bpp, cpl)
        print(f"  CPL={cpl:3d} -> Allocated BPP: {current_bpp} (Total bullets: {sum(current_bpp)}/{n*ideal_bpp}), Est Height: {h:.1f}pt / {USABLE_HEIGHT_PT}pt ({h/USABLE_HEIGHT_PT*100:.1f}%)")

conn.close()
