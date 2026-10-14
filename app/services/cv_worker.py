import os
import sys
import json
import sqlite3
import asyncio
from app.core.database import get_db_connection
from app.core.jobs_db import claim_next_job, update_job_result, update_job_status
from app.core.llm_client import TokenExhaustionError, execute_llm_request

SYSTEM_PROMPT_PATH = r"C:\Works\Hiring_Automation_Pipeline\HR_Automation_Pipeline\app\assests\CV_prompt.txt"


def get_target_jd() -> str:
    conn = cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT generated_JD FROM client_demands ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row and row["generated_JD"]:
            return row["generated_JD"]
    except Exception as e:
        print(f"Error fetching latest JD: {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()
    return (
        "Role: Business Analyst / Consultant\n"
        "Key requirements: Requirements gathering, stakeholder management, UAT testing support, "
        "business process mapping, Agile methodology, and functional specification documentation."
    )


def clean_candidate_name(raw_name: str) -> str:
    if not raw_name:
        return "Unknown Candidate"
    import re
    name = re.sub(r'\.(pdf|docx|txt|md|pptx)$', '', raw_name, flags=re.IGNORECASE)
    name = re.sub(r'\[[^\]]*\]', '', name)
    name = re.sub(r'\([^\)]*\)', '', name)
    name = re.sub(r'\b\d+\s*(y|yr|yrs|m|mon|months|month)\b', '', name, flags=re.IGNORECASE)
    for pattern in [
        r'\b(?:functional\s+tester|senior\s+credit\s+analyst|software\s+engineer|consultant|'
        r'risk\s+analyst|systems\s+engineer|manager|functional\s+specialist|fuctional\s+tester)\b',
        r'\b(?:three\s+across|two\s+across|four\s+across)\b',
    ]:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', name).strip()


def optimize_system_prompt(prompt: str) -> str:
    import re
    prompt = re.sub(r'=+\n', '', prompt)
    prompt = re.sub(
        r'(?:Before producing the final JSON output:|FINAL VALIDATION CHECK).*',
        '', prompt, flags=re.DOTALL | re.IGNORECASE
    )
    return '\n'.join(line for line in prompt.split('\n') if line.strip())


# ─────────────────────────────────────────────────────────────────────────────
# BULLET COUNT RULES — injected as explicit top-level instructions so the LLM
# treats them as commands, not as JSON schema documentation.
# ─────────────────────────────────────────────────────────────────────────────
BULLET_RULES = """
====================================================
MANDATORY BULLET GENERATION RULES — FOLLOW EXACTLY
====================================================
These rules override everything else for the bullets field.

STEP 1 — Count the total number of distinct projects in the candidate's CV.
STEP 2 — Apply the rule for that count:

  • CV has 1 or 2 projects total      → generate EXACTLY 5 to 6 comprehensive, multi-sentence, highly descriptive bullets per project (25–35 words each).
  • CV has 3 projects total           → generate EXACTLY 4 to 5 detailed bullets per project (20–30 words each).
  • CV has 4 or 5 projects total      → generate EXACTLY 3 to 4 substantial bullets per project (18–25 words each).
  • CV has 6 or more projects total   → generate EXACTLY 2 to 3 substantive bullets per project (15–20 words each).

STEP 3 — Every single bullet MUST:
  (a) Start with a strong past-tense action verb
      (e.g. Designed, Engineered, Led, Delivered, Developed, Implemented,
       Authored, Coordinated, Validated, Executed, Collaborated, Streamlined).
  (b) Describe a SPECIFIC, REAL responsibility, methodology, technical tool, or achievement from the CV.
  (c) Be a substantive, complete sentence (15+ words).
  (d) Contain NO ** bold markers whatsoever — plain text only.

STEP 4 — Do NOT skip any project from the CV. Every project must appear.

STEP 5 — Do NOT add fewer bullets than the rule requires.
          If the CV has limited detail or few projects, elaborate professionally
          and thoroughly using realistic domain context, standard business analyst / consultant methodologies,
          tools, architectures, testing, and metrics so the slide is fully and richly populated.
"""


def process_job_with_llm(job: dict, system_prompt: str, jd_text: str) -> dict:
    cleaned_name = clean_candidate_name(job.get('candidate_name'))

    # The bullet rules are injected as a standalone top-level block BEFORE the
    # JSON schema so the LLM reads them as mandatory instructions, not comments.
    full_system = (
        f"{system_prompt}\n\n"
        f"{BULLET_RULES}\n\n"
        f"====================================================\n"
        f"OUTPUT FORMAT — STRICT JSON ONLY\n"
        f"====================================================\n"
        f"Return ONLY a valid JSON object. No markdown, no text outside the braces.\n\n"
        f"JSON schema:\n"
        f"{{\n"
        f"  \"professional_summary\": \"100–120 word summary. Start: '<Name> has X years of experience...'. "
        f"FIRST SENTENCE ONLY may use **bold markers** on the most critical terms. "
        f"All other sentences: plain text, no ** markers.\",\n"
        f"  \"industry_expertise\": [\"2–4 industry domain strings\"],\n"
        f"  \"areas_of_expertise\": [\"exactly 20 short ATS keyword strings\"],\n"
        f"  \"education\": [\"1–3 degree titles exactly as written in the CV\"],\n"
        f"  \"major_project_experience\": [\n"
        f"    {{\n"
        f"      \"project_title\": \"<Industry Description> – <Project Theme>\",\n"
        f"      \"role\": \"role title only\",\n"
        f"      \"bullets\": [\n"
        f"        \"bullet 1 — plain text, 15+ words, starts with action verb\",\n"
        f"        \"bullet 2 — plain text, 15+ words, starts with action verb\",\n"
        f"        \"... (follow MANDATORY BULLET GENERATION RULES above for exact count)\"\n"
        f"      ]\n"
        f"    }}\n"
        f"  ]\n"
        f"}}\n"
    )

    user_content = (
        f"Candidate CV (raw text):\n{job['raw_text']}\n\n"
        f"Target Job Description:\n{jd_text}"
    )

    print("[LLM Worker] Querying API for standardised resume...")
    messages = [
        {"role": "system", "content": full_system},
        {"role": "user",   "content": user_content},
    ]

    # 8000 tokens: enough for 6 projects × 5 bullets × ~40 words each
    result_content = execute_llm_request(
        "resume", messages=messages,
        response_format={"type": "json_object"},
        max_tokens=8000
    )

    try:
        res_dict = json.loads(result_content)
    except json.JSONDecodeError as jde:
        print(f"[LLM Worker] JSON parse failed for {cleaned_name}: {jde}")
        print(f"[LLM Worker] Raw response:\n{result_content}")
        raise ValueError(
            f"Failed to parse LLM response as JSON. Error: {jde}\n"
            f"Raw LLM Response:\n{result_content}"
        )

    res_dict["candidate_name"] = cleaned_name

    # Log bullet counts per project for debugging
    projects = res_dict.get("major_project_experience", [])
    print(f"[LLM Worker] Projects returned: {len(projects)}")
    for i, p in enumerate(projects):
        bc = len(p.get("bullets", []))
        print(f"  Project {i+1}: '{str(p.get('project_title',''))[:50]}' — {bc} bullets")

    return res_dict


def calculate_semantic_match(result_json_str: str, jd_text: str) -> tuple:
    system_prompt = (
        "You are an expert technical recruiter. Compare a candidate's standardised resume profile "
        "against a target Job Description (JD).\n"
        "Calculate a match percentage score from 0 to 100.\n"
        "Provide a 1-sentence 'match_reason' (max 20 words).\n\n"
        "Respond ONLY with valid JSON: {\"match_score\": int, \"match_reason\": string}\n"
    )
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"JD:\n{jd_text}\n\nProfile:\n{result_json_str}"},
        ]
        response_content = execute_llm_request(
            "resume", messages=messages, response_format={"type": "json_object"}
        )
        result = json.loads(response_content)
        score  = max(0, min(100, int(result.get("match_score", 0))))
        reason = str(result.get("match_reason", "No reason provided.")).strip()
        return score, reason
    except Exception as e:
        print(f"Error calculating semantic match: {e}")
        return 0, f"Match evaluation failed: {str(e)}"


async def process_next_job_async() -> bool:
    job = claim_next_job()
    if not job:
        return False

    job_id         = job["id"]
    candidate_name = job["candidate_name"]
    print(f"[Worker] Claimed Job {job_id} for: {candidate_name} (Retry: {job['retry_count']})")

    try:
        if not os.path.exists(SYSTEM_PROMPT_PATH):
            raise FileNotFoundError(f"System prompt not found: {SYSTEM_PROMPT_PATH}")

        with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            system_prompt = f.read()

        jd_text = job.get("jd_text") or ""
        if not jd_text.strip():
            jd_text = get_target_jd()

        system_prompt_with_jd = system_prompt
        if "JD ALIGNMENT LOGIC" in system_prompt_with_jd:
            system_prompt_with_jd = system_prompt_with_jd.replace(
                "====================================================\n"
                "JD ALIGNMENT LOGIC\n"
                "====================================================",
                f"====================================================\n"
                f"JD ALIGNMENT LOGIC\n"
                f"====================================================\n\n"
                f"TARGET JOB DESCRIPTION (JD) FOR ALIGNMENT:\n{jd_text}\n"
            )

        system_prompt_with_jd = optimize_system_prompt(system_prompt_with_jd)

        loop = asyncio.get_running_loop()
        result_data = await loop.run_in_executor(
            None, process_job_with_llm, job, system_prompt_with_jd, jd_text
        )

        result_json_str = json.dumps(result_data)
        score, reason   = calculate_semantic_match(result_json_str, jd_text)
        update_job_result(job_id, result_json_str, match_score=score, match_reason=reason)
        print(f"[Worker] Job {job_id} completed. Match Score: {score}%.")

    except TokenExhaustionError as e:
        error_msg = f"TokenExhaustionError: API tokens exhausted. Retry after {e.retry_after}"
        print(f"[Worker] Job {job_id} failed: {error_msg}")
        update_job_status(job_id, "PENDING" if job["retry_count"] < 3 else "FAILED",
                          error_message=error_msg)
    except Exception as e:
        import traceback
        tb_str    = traceback.format_exc()
        error_msg = f"{type(e).__name__}: {str(e)}\nTraceback:\n{tb_str}"
        print(f"[Worker] Job {job_id} failed:\n{tb_str}")
        update_job_status(job_id, "PENDING" if job["retry_count"] < 3 else "FAILED",
                          error_message=error_msg)

    return True


async def start_worker_loop():
    print("[Worker] Background CV conversion worker started.")
    while True:
        try:
            job_processed = await process_next_job_async()
            await asyncio.sleep(0.1 if job_processed else 5.0)
        except Exception as e:
            print(f"[Worker] Critical error in main loop: {e}")
            await asyncio.sleep(10.0)


if __name__ == "__main__":
    print("Starting worker process...")
    from dotenv import load_dotenv
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(dotenv_path=os.path.join(base_dir, ".env"))
    sys.path.insert(0, base_dir)
    asyncio.run(start_worker_loop())