import os
import sys

# Ensure parent and project directories are in sys.path so `app` can be imported from anywhere
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
for p in [PROJECT_ROOT, os.path.dirname(PROJECT_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Explicitly ensure paths to installed package libraries are in search path
user_site_path = os.path.expanduser(r"~\AppData\Roaming\Python\Python314\site-packages")
win32_path = os.path.join(user_site_path, "win32")
win32_lib_path = os.path.join(user_site_path, "win32", "lib")
for p in [user_site_path, win32_path, win32_lib_path]:
    if p not in sys.path:
        sys.path.append(p)

import time
import subprocess
import uuid
import asyncio
import json
import re
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from app.core.llm_client import TokenExhaustionError, execute_llm_request
from fastapi.responses import JSONResponse
from app.services.parser import extract_text_from_pdf
from app.services.matcher import compare_cv_with_jd_async
from app.core.database import init_db, get_db_connection
from app.services.db_service import save_demand_and_jd, extract_keywords, get_all_history, get_demand_and_jd_by_id, delete_client_demand_by_id
from app.services.db_service import save_client_feedback, get_all_client_feedbacks, get_all_feedback_keywords
from app.services.feedback_service import analyze_client_feedback
from app.core.jobs_db import init_jobs_db, create_job, get_all_jobs, get_job_by_id, update_job_result, update_job_status, delete_job_by_id
from app.services.pdf_export_service import render_pptx_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load environment variables from the .env file in the root directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(BASE_DIR), ".env"))

app = FastAPI(title="HR AI Recruitment Portal")
main = app

@app.exception_handler(TokenExhaustionError)
def token_exhaustion_exception_handler(request, exc: TokenExhaustionError):
    return JSONResponse(
        status_code=429,
        content={
            "status": "exhausted",
            "retry_after": exc.retry_after,
            "message": exc.message
        }
    )

@app.on_event("startup")
def startup_event():
    init_db()
    init_jobs_db()
    from app.services.cv_worker import start_worker_loop
    asyncio.create_task(start_worker_loop())
FIXED_ROLE_LIST = [
    "Transaction Banking (FX BA)",
    "Transaction Banking (Payments BA)",
    "Transaction Banking (Payments BA - Ops specialization)",
    "PaymentsOps BA",
    "Transaction Banking",
    "Accounts BA",
    "Accounts BA (US Timezone)",
    "Accounts Ops Trf BA",
    "Asset Management (French speaking BA)",
    "Lending BA",
    "UK Lending BA",
    "South Asia BA",
    "Analytics BA",
    "Analytics (Data) BA",
    "Fraud and Collections (Oak)",
    "Global Fraud BA",
    "Digital & related CCT",
    "Channels BA",
    "UK Wealth",
    "UK SME Business Banking BA",
    "UK Generic BA",
    "Asset Management",
    "CCT - Conversation Banking",
    "Gen AI Automation BA",
]

FIXED_ROLE_LIST_STR = "\n".join(f"- {r}" for r in FIXED_ROLE_LIST)

SYSTEM_PROMPT = f"""You are an expert HR and Technical Recruiter. Your sole task is to generate professional, well-structured Job Descriptions (JDs) based on client demands.

CRITICAL RULE 1 — Job Title: The very first line of your response MUST be exactly in this format:
Job Title: <role name>

You MUST pick the role name from this fixed list only. Choose the closest matching role based on the demands:
{FIXED_ROLE_LIST_STR}

Do NOT invent a new role name. Do NOT use any name outside this list.

CRITICAL RULE 2 — Structure: After the Job Title line, output the JD with these sections:
1. Role Overview
2. Key Responsibilities (bullet points)
3. Required Skills & Qualifications (must-haves vs nice-to-haves)
4. Preferred Experience

Keep the tone professional, attractive to candidates, and highly organized. Do not add conversational filler before or after the JD.
"""


# Ollama service check removed as generation relies solely on Groq

# Mount the 'static' folder to serve HTML/CSS/JS assets
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/assests", StaticFiles(directory=os.path.join(BASE_DIR, "assests")), name="assests")

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GPT_OSS_20B") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail="GROQ_API_KEY or GPT_OSS_20B is missing."
        )
    base_url = os.getenv("GPT_OSS_20B_BASE_URL") or os.getenv("GROQ_API_BASE_URL") or "https://api.groq.com/openai/v1"
    return OpenAI(
        api_key=api_key,
        base_url=base_url
    )

def generate_jd_with_groq(prompt: str) -> str:
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        return execute_llm_request("general", messages=messages)
    except TokenExhaustionError:
        raise
    except Exception as e:
        raise Exception(f"LLM Provider API Error: {str(e)}")

def extract_matched_role(response_text: str) -> str:
    """
    Extracts the Job Title line from LLM response and matches it to the closest
    role in FIXED_ROLE_LIST. Falls back to the first role if nothing matches.
    """
    import re
    # Pull whatever the LLM wrote after "Job Title:"
    match = re.search(r"Job Title:\s*(.+)", response_text, re.IGNORECASE)
    if not match:
        return FIXED_ROLE_LIST[0]

    llm_title = match.group(1).strip().lower()

    # Exact match first
    for role in FIXED_ROLE_LIST:
        if role.lower() == llm_title:
            return role

    # Partial match — pick the role with most overlapping words
    best_role = FIXED_ROLE_LIST[0]
    best_score = 0
    llm_words = set(llm_title.split())
    for role in FIXED_ROLE_LIST:
        role_words = set(role.lower().split())
        score = len(llm_words & role_words)
        if score > best_score:
            best_score = score
            best_role = role

    return best_role

# Data format structure for receiving user web prompts
class DemandRequest(BaseModel):
    demands: str

@app.get("/")
def read_root():
    # Serves the main UI page when you visit http://127.0.0.1:8000
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))

@app.post("/generate")
def generate_jd(data: DemandRequest):
    if not data.demands.strip():
        raise HTTPException(status_code=400, detail="Demands payload cannot be empty")
    
    try:
        response_text = generate_jd_with_groq(data.demands)
        matched_role = extract_matched_role(response_text)
        keywords_list = extract_keywords(data.demands, response_text)
        inserted_id = save_demand_and_jd(data.demands, response_text, keywords_list)
        return {
            "response": response_text,
            "id": inserted_id,
            "keywords": keywords_list,
            "matched_role": matched_role
        }
    except TokenExhaustionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM Provider Error: {str(e)}")

@app.get("/api/roles")
def get_roles():
    return {"roles": FIXED_ROLE_LIST}

@app.get("/api/history")
def read_history():
    try:
        return get_all_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{record_id}")
def read_history_by_id(record_id: int):
    try:
        record = get_demand_and_jd_by_id(record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        return record
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/client-demands/{record_id}")
def api_delete_client_demand(record_id: int):
    try:
        success = delete_client_demand_by_id(record_id)
        if not success:
            raise HTTPException(status_code=404, detail="Record not found")
        return {"status": "success", "message": "Record permanently deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_single_resume(file: UploadFile, jd_text: str, provider: str, api_key: str, missing_keywords: list = None):
    if not file.filename.lower().endswith(".pdf"):
        raise ValueError(f"File {file.filename} is not a PDF.")

    os.makedirs("data", exist_ok=True)
    os.makedirs("app/static/uploads", exist_ok=True)
    temp_filename = f"data/temp_{uuid.uuid4().hex}.pdf"

    try:
        content = await file.read()
        with open(temp_filename, "wb") as f:
            f.write(content)

        # Save permanent copy for PDF viewer
        perm_path = os.path.join("app", "static", "uploads", file.filename)
        with open(perm_path, "wb") as f_perm:
            f_perm.write(content)

        cv_text = extract_text_from_pdf(temp_filename)
        if not cv_text.strip() or cv_text.startswith("Error"):
            raise ValueError(f"Failed to parse text from {file.filename}.")

        result = await compare_cv_with_jd_async(cv_text, jd_text, api_key, provider, missing_keywords=missing_keywords)
        
        result["cv_text"] = cv_text
        result["filename"] = file.filename
        return result
    finally:
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass

from app.services.pdf_service import create_resume_pdf

@app.get("/api/resumes/pdf/{filename}")
def get_resume_pdf(filename: str):
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"
        
    uploads_dir = os.path.join("app", "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    filepath = os.path.join(uploads_dir, filename)
    
    if not os.path.exists(filepath):
        clean_name = filename.rsplit('.', 1)[0].replace("_", " ")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT resume_text FROM candidates WHERE name LIKE ? OR email LIKE ?", 
                       (f"%{clean_name}%", f"%{clean_name}%"))
        row = cursor.fetchone()
        conn.close()
        
        resume_text = row["resume_text"] if row and row["resume_text"] else f"{clean_name}\n\nOfficial Resume & Candidate Evaluation File."
        create_resume_pdf(clean_name, resume_text, filepath)
        
    return FileResponse(filepath, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=\"{filename}\""})


@app.post("/api/compare-upload")
async def compare_upload(
    files: list[UploadFile] = File(...),
    jd_text: str = Form(...),
    provider: str = Form("groq"),
    use_feedback_keywords: bool = Form(True),
    missing_keywords: str = Form("")
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    api_key = os.getenv("GROQ_API_KEY")

    # Parse HR-provided "Missing Keywords" (comma or newline separated) into a clean list.
    hr_keywords = [k.strip() for k in re.split(r'[,\n]+', missing_keywords or "") if k.strip()]

    # Augment the JD with out-of-the-box keywords gathered from past client feedback.
    # This feeds the cosine + deep-LLM screening with the "hidden" skills clients asked
    # about in previous interview cycles.
    screening_jd = jd_text
    if use_feedback_keywords:
        try:
            kw = get_all_feedback_keywords()
            labels = {
                "hard_skills": "Additional Hard Skills",
                "soft_skills": "Additional Soft Skills",
                "domain_knowledge": "Additional Domain Knowledge",
                "behavioral_knowledge": "Additional Behavioural Expectations",
            }
            appendix = ["\n\n--- CLIENT FEEDBACK INSIGHTS (out-of-the-box skills from past interviews) ---"]
            for key, label in labels.items():
                if kw.get(key):
                    appendix.append(f"{label}: {', '.join(kw[key])}")
            if len(appendix) > 1:
                screening_jd = jd_text + "\n".join(appendix)
        except Exception:
            pass

    tasks = [process_single_resume(file, screening_jd, provider, api_key, missing_keywords=hr_keywords) for file in files]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_results = []
    errors = []
    for r in results:
        if isinstance(r, TokenExhaustionError):
            raise r
        elif isinstance(r, Exception):
            errors.append(str(r))
        else:
            valid_results.append(r)
            
    if not valid_results:
        raise HTTPException(status_code=400, detail=f"All uploads failed: {'; '.join(errors)}")
        
    return valid_results


# Import cognitive engine functions & sub-agents
from app.services.cognitive_engine import (
    run_resume_evaluation,
    run_email_generation,
    run_feedback_standardization,
    run_progressive_prep_assembly,
    run_final_consolidation,
    run_session_initializer_agent,
    run_progressive_prep_agent,
    run_email_generator_agent,
    run_feedback_standardization_agent,
    run_session_consolidation_agent,
    run_role_alignment_agent,
    run_error_handler
)

class ResumeEvaluationRequest(BaseModel):
    resume_text: str
    job_description: str

@app.post("/api/resume-evaluation")
def api_resume_evaluation(data: ResumeEvaluationRequest):
    try:
        return run_resume_evaluation(data.resume_text, data.job_description)
    except TokenExhaustionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class EmailGenerationRequest(BaseModel):
    action: str
    candidate_name: str
    candidate_email: str
    role_name: str
    prep_questions: list[str] = None

@app.post("/api/email-generation")
def api_email_generation(data: EmailGenerationRequest):
    try:
        return run_email_generation(data.action, data.candidate_name, data.candidate_email, data.role_name, data.prep_questions)
    except TokenExhaustionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class FeedbackStandardizationRequest(BaseModel):
    raw_feedback: str
    candidate_id: str
    session_id: str

@app.post("/api/feedback-standardization")
def api_feedback_standardization(data: FeedbackStandardizationRequest):
    try:
        return run_feedback_standardization(data.raw_feedback, data.session_id, data.candidate_id)
    except TokenExhaustionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ProgressivePrepRequest(BaseModel):
    historical_questions: list[dict]
    current_session_questions: list[dict]

@app.post("/api/progressive-prep-assembly")
def api_progressive_prep_assembly(data: ProgressivePrepRequest):
    try:
        return run_progressive_prep_assembly(data.historical_questions, data.current_session_questions)
    except TokenExhaustionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class FinalConsolidationRequest(BaseModel):
    all_session_questions: list[dict]
    master_questions: list[dict]

@app.post("/api/final-consolidation")
def api_final_consolidation(data: FinalConsolidationRequest):
    try:
        res = run_final_consolidation(data.all_session_questions, data.master_questions)
        db_updates = res.get("database_updates", {"inserts": [], "updates": []})
        
        # Build a mapping of question text to its existing category from master_questions
        master_type_map = {q.get("question_text"): q.get("category") for q in data.master_questions if q.get("question_text")}
        
        updates_to_master = []
        for item in db_updates.get("inserts", []):
            q_text = item.get("question_text")
            if not q_text or not isinstance(q_text, str):
                continue
            category_val = item.get("category", "").upper()
            norm_cat = "DOMAIN" if "DOMAIN" in category_val else "GENERIC"
            updates_to_master.append({
                "question_text": q_text,
                "category": norm_cat,
                "action": "INSERT",
                "frequency_count": item.get("initial_frequency", 1)
            })
        for item in db_updates.get("updates", []):
            q_text = item.get("question_text")
            if not q_text or not isinstance(q_text, str):
                continue
            existing_cat = master_type_map.get(q_text, "GENERIC")
            updates_to_master.append({
                "question_text": q_text,
                "category": existing_cat,
                "action": "UPDATE",
                "frequency_count": item.get("increment_by", 1)
            })
            
        return {
            "pdf_structure": res.get("pdf_structure"),
            "updates_to_master": updates_to_master
        }
    except TokenExhaustionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AcceptCandidateRequest(BaseModel):
    name: str
    email: str
    role: str
    resume_text: str = None
    resume_score: int = None
    reasoning: str = None

@app.post("/api/candidates/accept")
def api_accept_candidate(data: AcceptCandidateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Always reuse existing session for this role — never create duplicates
        cursor.execute("SELECT id, total_candidates FROM interview_sessions WHERE role = ?", (data.role,))
        session_row = cursor.fetchone()
        if session_row:
            session_id = session_row["id"]
            cursor.execute("UPDATE interview_sessions SET total_candidates = total_candidates + 1 WHERE id = ?", (session_id,))
        else:
            cursor.execute("INSERT INTO interview_sessions (role, total_candidates, completed_candidates, status) VALUES (?, ?, ?, ?)",
                           (data.role, 1, 0, "Active"))
            session_id = cursor.lastrowid
            
        # Insert the candidate linked to this session
        cursor.execute(
            "INSERT INTO candidates (session_id, name, email, resume_text, status, resume_score, reasoning) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, data.name, data.email, data.resume_text, "Accept", data.resume_score, data.reasoning)
        )
        conn.commit()
        
        # Generate the accept email
        email_data = run_email_generation(
            action="ACCEPT",
            candidate_name=data.name,
            candidate_email=data.email,
            role_name=data.role,
            prep_questions=[]
        )
        return {
            "status": "success",
            "session_id": session_id,
            "email": email_data
        }
    except TokenExhaustionError:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# -------------------------------------------------------------------
# REGISTERED SUB-AGENT ENDPOINTS (Antigravity AI Harness Engine)
# -------------------------------------------------------------------

class SessionInitializerAgentRequest(BaseModel):
    role_name: str
    raw_candidate_list: list

@app.post("/api/agent/session-initializer")
def api_agent_session_initializer(data: SessionInitializerAgentRequest):
    return run_session_initializer_agent(data.role_name, data.raw_candidate_list)

class ProgressivePrepAgentRequest(BaseModel):
    candidate_name: str
    role_name: str
    sequence_number: int
    excel_baseline_questions: list[dict] = None
    previous_candidates_questions: list[dict] = None

@app.post("/api/agent/progressive-prep")
def api_agent_progressive_prep(data: ProgressivePrepAgentRequest):
    return run_progressive_prep_agent(
        data.candidate_name,
        data.role_name,
        data.sequence_number,
        data.excel_baseline_questions,
        data.previous_candidates_questions
    )

class EmailGeneratorAgentRequest(BaseModel):
    action: str
    candidate_name: str
    candidate_email: str
    role_name: str
    prep_questions: list[dict] = None

@app.post("/api/agent/email-generator")
def api_agent_email_generator(data: EmailGeneratorAgentRequest):
    return run_email_generator_agent(
        data.action,
        data.candidate_name,
        data.candidate_email,
        data.role_name,
        data.prep_questions
    )

class FeedbackStandardizationAgentRequest(BaseModel):
    raw_feedback_text: str
    session_id: str
    candidate_id: str

@app.post("/api/agent/feedback-standardization")
def api_agent_feedback_standardization(data: FeedbackStandardizationAgentRequest):
    return run_feedback_standardization_agent(
        data.raw_feedback_text,
        data.session_id,
        data.candidate_id
    )

class SessionConsolidationAgentRequest(BaseModel):
    session_questions: list[dict]
    master_questions: list[dict]

@app.post("/api/agent/session-consolidation")
def api_agent_session_consolidation(data: SessionConsolidationAgentRequest):
    return run_session_consolidation_agent(
        data.session_questions,
        data.master_questions
    )




@app.get("/api/sessions")
def api_get_sessions():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM interview_sessions")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

class CreateSessionRequest(BaseModel):
    role: str
    total_candidates: int

@app.post("/api/sessions")
def api_create_session(data: CreateSessionRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO interview_sessions (role, total_candidates, completed_candidates, status) VALUES (?, ?, ?, ?)",
                       (data.role, data.total_candidates, 0, "Active"))
        conn.commit()
        session_id = cursor.lastrowid
        cursor.execute("SELECT * FROM interview_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row)
    finally:
        conn.close()

@app.get("/api/sessions/{session_id}/candidates")
def api_get_session_candidates(session_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM candidates WHERE session_id = ? ORDER BY id ASC", (session_id,))
        rows = cursor.fetchall()
        candidates = []
        for idx, row in enumerate(rows, start=1):
            cand = dict(row)
            cand["sequence_number"] = idx
            candidates.append(cand)
        return candidates
    finally:
        conn.close()

@app.get("/api/sessions/{session_id}/questions")
def api_get_session_questions(session_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM session_questions WHERE session_id = ?", (session_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

@app.get("/api/master-questions")
def api_get_master_questions():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM master_questions")
        rows = cursor.fetchall()
        # Map database schema columns (type, frequency) to expected UI keys (category, frequency_count)
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "question_text": row["question_text"],
                "category": row["type"],
                "frequency_count": row["frequency"],
                "type": row["type"],
                "frequency": row["frequency"]
            })
        return result
    finally:
        conn.close()


class SaveMasterQuestionsRequest(BaseModel):
    general_questions: str
    domain_questions: str

@app.post("/api/master-questions/save")
def api_save_master_questions(data: SaveMasterQuestionsRequest):
    import re
    from app.services.db_service import save_to_master_db
    try:
        gen_list = [q.strip() for q in re.split(r'[\n;]+', data.general_questions) if q.strip()]
        dom_list = [q.strip() for q in re.split(r'[\n;]+', data.domain_questions) if q.strip()]
        
        for q in gen_list:
            save_to_master_db(q, "GENERIC")
        for q in dom_list:
            save_to_master_db(q, "DOMAIN")
            
        return {"status": "SUCCESS", "generic_saved": len(gen_list), "domain_saved": len(dom_list)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SendSessionQuestionsRequest(BaseModel):
    session_id: int
    candidate_id: int
    general_questions: str
    domain_questions: str

@app.post("/api/session-questions/save")
def api_save_session_questions(data: SendSessionQuestionsRequest):
    import re
    try:
        gen_list = [q.strip() for q in re.split(r'[\n;]+', data.general_questions) if q.strip()]
        dom_list = [q.strip() for q in re.split(r'[\n;]+', data.domain_questions) if q.strip()]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        for q in gen_list:
            cursor.execute(
                "INSERT INTO session_questions (session_id, candidate_id, raw_text, standardized_question, category) VALUES (?, ?, ?, ?, ?)",
                (data.session_id, data.candidate_id, "Manual input", q, "General")
            )
        for q in dom_list:
            cursor.execute(
                "INSERT INTO session_questions (session_id, candidate_id, raw_text, standardized_question, category) VALUES (?, ?, ?, ?, ?)",
                (data.session_id, data.candidate_id, "Manual input", q, "Domain")
            )
        conn.commit()
        conn.close()
        return {"status": "SUCCESS", "generic_saved": len(gen_list), "domain_saved": len(dom_list)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/role-alignment")
async def api_role_alignment(
    candidate_name: str = Form(...),
    file: UploadFile = File(...)
):
    temp_dir = os.path.join(BASE_DIR, "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    filename = file.filename
    temp_file_path = os.path.join(temp_dir, filename)
    try:
        with open(temp_file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        from app.services.parser import extract_text_from_file
        raw_text = extract_text_from_file(temp_file_path)
        
        if raw_text.startswith("Error"):
            raise HTTPException(status_code=400, detail=f"Failed to parse resume file: {raw_text}")
            
        result = run_role_alignment_agent(candidate_name, raw_text, "")
        if result.get("status") == "FAILED":
            raise HTTPException(status_code=400, detail=result.get("error", {}).get("message", "Role alignment failed"))
        return result
    except TokenExhaustionError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass


class ClientFeedbackRequest(BaseModel):
    original_demand: str = ""
    raw_feedback: str
    similarity_threshold: float = 0.30
    save: bool = False

@app.post("/api/client-feedback/analyze")
def api_client_feedback_analyze(data: ClientFeedbackRequest):
    """
    Compares post-interview client feedback against the original demand and
    categorizes any out-of-the-box skills into keyword buckets.
    Two-layer: cosine similarity pre-filter -> deep LLM semantic categorization.

    By default this does NOT persist — results are returned for human review first.
    HR reviews/edits the keywords in the UI, then calls /api/client-feedback/save.
    """
    if not data.raw_feedback or not data.raw_feedback.strip():
        raise HTTPException(status_code=400, detail="raw_feedback is required.")

    try:
        result = analyze_client_feedback(
            original_demand=data.original_demand,
            raw_feedback=data.raw_feedback,
            similarity_threshold=data.similarity_threshold
        )
    except TokenExhaustionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result.get("status") == "FAILED":
        raise HTTPException(status_code=400, detail=result.get("error", "Feedback analysis failed."))

    feedback_id = None
    if data.save and result.get("summary", {}).get("has_new_skills", False):
        try:
            feedback_id = save_client_feedback(
                original_demand=data.original_demand,
                raw_feedback=data.raw_feedback,
                categories=result.get("keywords", {}),
                reasoning=result.get("summary", {}).get("reasoning", "")
            )
        except Exception as e:
            result["db_save_warning"] = str(e)

    result["feedback_id"] = feedback_id
    return result


class ClientFeedbackKeywords(BaseModel):
    hard_skills: list = []
    soft_skills: list = []
    domain_knowledge: list = []
    behavioral_knowledge: list = []

class ClientFeedbackSaveRequest(BaseModel):
    original_demand: str = ""
    raw_feedback: str
    keywords: ClientFeedbackKeywords
    reasoning: str = ""
    candidate_name: str = ""
    role: str = ""

@app.post("/api/client-feedback/save")
def api_client_feedback_save(data: ClientFeedbackSaveRequest):
    """
    Persists the HUMAN-REVIEWED keywords for a client feedback (human-in-the-loop).
    Called after HR edits/re-categorizes/adds keywords in the UI and clicks Save.
    """
    if not data.raw_feedback or not data.raw_feedback.strip():
        raise HTTPException(status_code=400, detail="raw_feedback is required.")

    categories = {
        "hard_skills": [str(x).strip() for x in data.keywords.hard_skills if str(x).strip()],
        "soft_skills": [str(x).strip() for x in data.keywords.soft_skills if str(x).strip()],
        "domain_knowledge": [str(x).strip() for x in data.keywords.domain_knowledge if str(x).strip()],
        "behavioral_knowledge": [str(x).strip() for x in data.keywords.behavioral_knowledge if str(x).strip()],
    }

    total = sum(len(v) for v in categories.values())
    if total == 0:
        raise HTTPException(status_code=400, detail="Cannot save empty keywords. Add at least one keyword.")

    reasoning = data.reasoning or "Reviewed and confirmed by HR."
    try:
        feedback_id = save_client_feedback(
            original_demand=data.original_demand,
            raw_feedback=data.raw_feedback,
            categories=categories,
            reasoning=reasoning,
            candidate_name=data.candidate_name,
            role=data.role
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "SUCCESS", "feedback_id": feedback_id, "saved_keyword_count": total}



@app.get("/api/client-feedback/history")
def api_client_feedback_history():
    """Returns all stored client feedback records (most recent first)."""
    try:
        return {"feedbacks": get_all_client_feedbacks()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def extract_candidate_name_from_text(text: str, filename: str) -> str:
    """
    Attempts to extract candidate name from raw text using regex/patterns.
    Falls back to a clean version of the filename if no name is found.
    """
    patterns = [
        r"Name\s*:\s*([^\n\r]+)",
        r"Candidate Name\s*:\s*([^\n\r]+)",
        r"Full Name\s*:\s*([^\n\r]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            name = re.sub(r"[^\w\s\.-]", "", name).strip()
            if name:
                return name
                
    # Fallback: parse filename (e.g., "John_Doe_CV.pdf" -> "John Doe")
    base = os.path.splitext(filename)[0]
    base_clean = re.sub(r"\b(cv|resume|standard|standardized|final|draft)\b", "", base, flags=re.IGNORECASE)
    base_clean = re.sub(r"\b\d+\b", "", base_clean)
    base_clean = re.sub(r"\bv\d+\b", "", base_clean)
    base_clean = re.sub(r"[-_]+", " ", base_clean).strip()
    words = [w.capitalize() for w in base_clean.split() if w]
    if words:
        return " ".join(words)
        
    return "Unknown Candidate"


def extract_email_from_text(text: str, candidate_name: str) -> str:
    """Attempts to extract candidate email from raw text using regex. Falls back to a placeholder if none found."""
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    if match:
        return match.group(0).strip().lower()
    
    # Fallback placeholder email based on candidate name to satisfy UNIQUE constraint safely
    clean_name = re.sub(r"[^\w]", "", candidate_name).lower()
    if not clean_name:
        clean_name = "unknown"
    return f"{clean_name}_no_email@placeholder.com"


class JobUpdateRequest(BaseModel):
    result_json: dict | str


@app.post("/api/upload-cv")
async def upload_cv(
    files: list[UploadFile] = File(...),
    jd_text: str = Form(""),
    jd_file: UploadFile | None = File(None)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
        
    # If jd_file is provided, extract text from it
    if jd_file and jd_file.filename:
        temp_dir = os.path.join(BASE_DIR, "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        temp_jd_path = os.path.join(temp_dir, "jd_" + jd_file.filename)
        try:
            with open(temp_jd_path, "wb") as f:
                content = await jd_file.read()
                f.write(content)
                
            from app.services.parser import extract_text_from_file
            extracted_jd = extract_text_from_file(temp_jd_path)
            if not extracted_jd.startswith("Error"):
                jd_text = extracted_jd
            else:
                print(f"Failed to extract JD from file: {extracted_jd}")
        except Exception as e:
            print(f"Exception during JD extraction: {str(e)}")
        finally:
            if os.path.exists(temp_jd_path):
                try:
                    os.remove(temp_jd_path)
                except Exception:
                    pass
        
    job_ids = []
    errors = []
    
    # Use workspace temporary uploads directory
    temp_dir = os.path.join(BASE_DIR, "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    for file in files:
        filename = file.filename
        if not (filename.lower().endswith('.pdf') or filename.lower().endswith('.docx') or filename.lower().endswith('.txt') or filename.lower().endswith('.md')):
            errors.append(f"Unsupported file format for {filename}")
            continue
            
        temp_file_path = os.path.join(temp_dir, filename)
        try:
            with open(temp_file_path, "wb") as f:
                content = await file.read()
                f.write(content)
                
            from app.services.parser import extract_text_from_file
            raw_text = extract_text_from_file(temp_file_path)
            
            if raw_text.startswith("Error"):
                errors.append(f"Failed to parse {filename}: {raw_text}")
                continue
                
            candidate_name = extract_candidate_name_from_text(raw_text, filename)
            email = extract_email_from_text(raw_text, candidate_name)
            
            job_id = create_job(candidate_name=candidate_name, email=email, raw_text=raw_text, jd_text=jd_text)
            job_ids.append(job_id)
            
        except Exception as e:
            errors.append(f"Failed processing {filename}: {str(e)}")
        finally:
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass
                    
    if not job_ids and errors:
        raise HTTPException(status_code=400, detail=f"Failed to process any CVs: {'; '.join(errors)}")
        
    return {
        "job_ids": job_ids,
        "processed_count": len(job_ids),
        "errors": errors if errors else None
    }


@app.get("/api/jobs")
def list_jobs():
    try:
        return get_all_jobs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{id}")
def get_job(id: int):
    try:
        job = get_job_by_id(id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with ID {id} not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int):
    """
    DELETE endpoint to remove a candidate job and delete their associated temporary rendered files.
    """
    try:
        # 1. Fetch job to extract the candidate name for file cleanup
        job = get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
            
        candidate_name = job.get("candidate_name") or "Candidate"
        
        # 2. Delete database row
        success = delete_job_by_id(job_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete job from database")
            
        # 3. Clean up any rendered .pptx files in app/temp for this candidate
        cleaned_name = re.sub(r'[^\w\s-]', '', candidate_name).strip()
        cleaned_name = re.sub(r'[\s-]+', '_', cleaned_name)
        
        temp_dir = os.path.join(BASE_DIR, "temp")
        deleted_files = []
        if os.path.exists(temp_dir):
            import glob
            # Match any files starting with cleaned_name in the temp folder
            pattern = os.path.join(temp_dir, f"{cleaned_name}*.pptx")
            for file_path in glob.glob(pattern):
                try:
                    os.remove(file_path)
                    deleted_files.append(os.path.basename(file_path))
                except Exception as e:
                    print(f"Error removing temp file {file_path}: {e}")
                    
        return {
            "status": "SUCCESS",
            "message": f"Successfully deleted candidate job #{job_id}",
            "deleted_temp_files": deleted_files
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/jobs/{id}")
def update_job_edited_result(id: int, payload: JobUpdateRequest):
    try:
        job = get_job_by_id(id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with ID {id} not found")
            
        res_data = payload.result_json
        if isinstance(res_data, dict):
            res_json_str = json.dumps(res_data)
        else:
            try:
                json.loads(res_data)
                res_json_str = res_data
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON format for result_json")
                
        success = update_job_result(id, res_json_str)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update job record")
            
        return {"status": "success", "message": f"Job {id} updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}/download-pptx")
async def download_job_pptx(job_id: int, background_tasks: BackgroundTasks):
    """
    GET endpoint to retrieve a completed job's result_json, inject it into the PowerPoint template,
    and serve the native PPTX presentation directly, cleaning up intermediate files afterward.
    """
    try:
        # 1. Fetch job details from SQLite
        job = get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found.")
            
        # 2. Check that the job status is COMPLETED
        if job.get("status") != "COMPLETED":
            raise HTTPException(
                status_code=400, 
                detail=f"Job is not completed yet. Current status: {job.get('status')}"
            )
            
        # 3. Parse result_json
        result_json_str = job.get("result_json")
        if not result_json_str:
            raise HTTPException(status_code=400, detail="Job has no standardized result JSON.")
            
        try:
            data = json.loads(result_json_str)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to parse result_json.")
            
        # 4. Normalize and clean the candidate's name for safe filename usage
        candidate_name = data.get("candidate_name") or job.get("candidate_name") or "Candidate"
        if "candidate_name" not in data or not data["candidate_name"]:
            data["candidate_name"] = candidate_name
        cleaned_name = re.sub(r'[^\w\s-]', '', candidate_name).strip()
        cleaned_name = re.sub(r'[\s-]+', '_', cleaned_name)
        
        # 5. Locate PPTX template file
        template_path = os.path.join(BASE_DIR, "assests", "Protiviti_Format_Resume.pptx")
        if not os.path.exists(template_path):
            raise HTTPException(status_code=500, detail=f"Template file not found at {template_path}")
            
        # 6. Setup temp output directory and unique file paths
        temp_dir = os.path.join(BASE_DIR, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_pptx_path = os.path.join(temp_dir, f"{cleaned_name}_Protiviti_format.pptx")
        
        # 7. Render values into the PowerPoint presentation
        try:
            render_pptx_template(data, template_path, temp_pptx_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to populate presentation template: {str(e)}")
            
        # 8. Schedule cleanup task for the temporary file
        def cleanup_temp_files(paths: list[str]):
            for p in paths:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception as e:
                        print(f"Error removing temporary file {p}: {e}")
                        
        background_tasks.add_task(cleanup_temp_files, [temp_pptx_path])
        
        # 9. Serve the PPTX response
        filename = f"{candidate_name}_Protiviti_format.pptx"
        return FileResponse(
            temp_pptx_path, 
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", 
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}/download-pdf")
async def download_job_pdf_compatibility_alias(job_id: int, background_tasks: BackgroundTasks):
    """Backward-compatible alias to support client browsers that have cached the old PDF endpoint."""
    return await download_job_pptx(job_id, background_tasks)


