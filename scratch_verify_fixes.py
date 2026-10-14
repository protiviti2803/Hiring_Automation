import sqlite3
import json
import os
import subprocess
from app.services.pdf_export_service import render_pptx_template

template_path = os.path.abspath("app/assests/Protiviti_Format_Resume.pptx")

conn = sqlite3.connect('resume_analyzer.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT id, candidate_name, result_json FROM cv_jobs WHERE status="COMPLETED"')
jobs = cur.fetchall()

print(f"Testing {len(jobs)} completed candidate resumes...")

for j in jobs:
    jid = j['id']
    cand_name = j['candidate_name'].encode('ascii', errors='replace').decode('ascii')
    print(f"\n=======================================================")
    print(f"Testing Job {jid}: {cand_name}")
    print(f"=======================================================")
    data = json.loads(j['result_json'])
    out_pptx = os.path.abspath(f"app/temp/final_verified_job_{jid}.pptx")
    out_pdf = os.path.abspath(f"app/temp/final_verified_job_{jid}.pdf")
    
    render_pptx_template(data, template_path, out_pptx)
    print(f"Saved PPTX to: {out_pptx}")
    
    # Convert to PDF
    res = subprocess.run(["python", "app/services/convert_pptx.py", out_pptx, out_pdf], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Converted to PDF: {out_pdf}")
    else:
        print(f"PDF conversion failed: {res.stderr}")

conn.close()
