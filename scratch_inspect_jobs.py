import sqlite3
import json

conn = sqlite3.connect('resume_analyzer.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT id, candidate_name, status, match_score, length(raw_text) as raw_len, result_json FROM cv_jobs ORDER BY id DESC LIMIT 10')
rows = cur.fetchall()
for r in rows:
    print(f"ID: {r['id']}, Name: {r['candidate_name']}, Status: {r['status']}, Match: {r['match_score']}")
    if r['result_json']:
        try:
            data = json.loads(r['result_json'])
            summary = data.get('professional_summary', '')
            projs = data.get('major_project_experience', [])
            print(f"  Summary ({len(summary)} chars, {len(summary.split())} words): {summary[:100]}...")
            print(f"  Projects ({len(projs)}):")
            for i, p in enumerate(projs):
                title = p.get('project_title') or p.get('title')
                role = p.get('role')
                bullets = p.get('bullets', [])
                print(f"    [{i+1}] Title: {title} | Role: {role} | Bullets: {len(bullets)}")
                for bi, b in enumerate(bullets):
                    if isinstance(b, str):
                        print(f"        b{bi+1} ({len(b)} chars): {b[:100]}...")
                    else:
                        print(f"        b{bi+1} (type {type(b)}): {b}")
        except Exception as e:
            print(f"  JSON parse error: {e}")
conn.close()
