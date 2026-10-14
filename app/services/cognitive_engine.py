import os
import json
import re
import sqlite3
from app.core.database import get_db_connection
from app.core.llm_client import TokenExhaustionError, execute_llm_request

# -------------------------------------------------------------------
# EXCEL QUESTION LOADER (Demands_Questions.xlsx)
# -------------------------------------------------------------------
def load_excel_questions_for_role(role_name: str) -> list:
    """
    Parses Demands_Questions.xlsx and returns baseline questions filtered specifically for role_name.
    """
    excel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assests", "Demands_Questions.xlsx")
    if not os.path.exists(excel_path):
        return []
    
    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_path)
        if "Interview Question" not in wb.sheetnames:
            return []
        sheet = wb["Interview Question"]
        
        role_questions = []
        role_name_clean = role_name.strip().lower()
        
        is_ba = "ba" in role_name_clean or "analyst" in role_name_clean
        is_pmo = "pmo" in role_name_clean
        is_pm = ("pm" in role_name_clean or "manager" in role_name_clean) and not is_pmo
        
        for r in range(2, sheet.max_row + 1):
            sheet_role = str(sheet.cell(r, 2).value or "").strip().lower()
            q_raw = sheet.cell(r, 3).value
            if not sheet_role or not q_raw:
                continue
                
            matched = False
            if role_name_clean in sheet_role:
                matched = True
            elif is_pmo and "pmo" in sheet_role:
                matched = True
            elif is_ba and ("ba" in sheet_role or "analyst" in sheet_role) and not "pmo" in sheet_role:
                matched = True
            elif is_pm and ("pm" in sheet_role or "manager" in sheet_role) and not "pmo" in sheet_role:
                matched = True
                
            if matched:
                lines = [l.strip() for l in str(q_raw).split("\n") if l.strip()]
                for l in lines:
                    cleaned_q = re.sub(r'^\d+[\.\)\s]*', '', l).strip()
                    if len(cleaned_q) > 8 and not cleaned_q.lower().startswith("panelist") and not cleaned_q.lower().startswith("role"):
                        role_questions.append({
                            "question_text": cleaned_q,
                            "category": "Domain" if ("understanding" in cleaned_q.lower() or "role" in cleaned_q.lower()) else "General",
                            "source": "EXCEL_BASELINE"
                        })
                        
        return role_questions
    except Exception as e:
        print(f"Error loading Excel questions: {e}")
        return []

# -------------------------------------------------------------------
# ERROR HANDLER SUB-ROUTINE
# -------------------------------------------------------------------
def run_error_handler(code: str, message: str) -> dict:
    return {
        "agent_execution": "ERROR_HANDLER",
        "status": "FAILED",
        "error": {
            "code": code,
            "message": message
        }
    }

# -------------------------------------------------------------------
# SUB-AGENT 1: SESSION_INITIALIZER_AGENT
# -------------------------------------------------------------------
def run_session_initializer_agent(role_name: str, raw_candidate_list: list) -> dict:
    if not role_name or not isinstance(role_name, str) or not role_name.strip():
        return run_error_handler("MISSING_PARAMETER", "role_name is required and must be a non-empty string for SESSION_INITIALIZER_AGENT.")
    
    if raw_candidate_list is None or not isinstance(raw_candidate_list, list):
        return run_error_handler("INVALID_TYPE", "raw_candidate_list must be a list for SESSION_INITIALIZER_AGENT.")

    role_name = role_name.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if session card for this role already exists
        cursor.execute("SELECT id, total_candidates FROM interview_sessions WHERE role = ?", (role_name,))
        existing_session = cursor.fetchone()
        
        if existing_session:
            session_id = existing_session["id"]
            new_total = existing_session["total_candidates"] + len(raw_candidate_list)
            cursor.execute("UPDATE interview_sessions SET total_candidates = ? WHERE id = ?", (new_total, session_id))
        else:
            cursor.execute(
                "INSERT INTO interview_sessions (role, total_candidates, completed_candidates, status) VALUES (?, ?, ?, ?)",
                (role_name, len(raw_candidate_list), 0, "Active")
            )
            session_id = cursor.lastrowid
        
        assigned_candidates = []
        for cand in raw_candidate_list:
            cand_name = cand.get("name") if isinstance(cand, dict) else str(cand)
            cand_email = cand.get("email", f"{cand_name.lower().replace(' ', '')}@example.com") if isinstance(cand, dict) else f"{cand_name.lower().replace(' ', '')}@example.com"
            
            cursor.execute(
                "INSERT INTO candidates (session_id, name, email, status) VALUES (?, ?, ?, ?)",
                (session_id, cand_name, cand_email, "SME_Pending")
            )
            assigned_candidates.append({
                "name": cand_name,
                "status": "SME_Pending"
            })
            
        conn.commit()
        
        return {
            "agent_execution": "SESSION_INITIALIZER_AGENT",
            "status": "SUCCESS",
            "session_card": {
                "role_name": role_name,
                "total_candidates": len(raw_candidate_list),
                "pipeline_status": "Active"
            },
            "assigned_candidates": assigned_candidates
        }
    except Exception as e:
        conn.rollback()
        return run_error_handler("EMPTY_INPUT", f"Failed to initialize session: {str(e)}")
    finally:
        conn.close()

# -------------------------------------------------------------------
# SUB-AGENT 2: PROGRESSIVE_PREP_AGENT (Excel + Cumulative Loop Logic)
# -------------------------------------------------------------------
def run_progressive_prep_agent(
    candidate_name: str,
    role_name: str,
    sequence_number: int,
    excel_baseline_questions: list = None,
    previous_candidates_questions: list = None
) -> dict:
    if not candidate_name or not isinstance(candidate_name, str) or not candidate_name.strip():
        return run_error_handler("MISSING_PARAMETER", "candidate_name is required for PROGRESSIVE_PREP_AGENT.")
        
    if not role_name or not isinstance(role_name, str) or not role_name.strip():
        return run_error_handler("MISSING_PARAMETER", "role_name is required for PROGRESSIVE_PREP_AGENT.")
        
    if sequence_number is None or not isinstance(sequence_number, int) or sequence_number < 1:
        return run_error_handler("INVALID_TYPE", "sequence_number must be an integer >= 1 for PROGRESSIVE_PREP_AGENT.")

    excel_baseline_questions = excel_baseline_questions or []
    previous_candidates_questions = previous_candidates_questions or []

    import uuid
    from app.services.progressive_interview_system import ProgressiveInterviewSystem
    system = ProgressiveInterviewSystem()

    # Load baseline questions
    if not excel_baseline_questions:
        excel_baseline_questions = load_excel_questions_for_role(role_name)

    # 1. Fetch current question frequencies and types from master_questions DB to initialize correctly
    db_questions_data = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT question_text, frequency, type FROM master_questions")
        db_questions_data = {row["question_text"]: (row["frequency"], row["type"]) for row in cursor.fetchall()}
        conn.close()
    except Exception:
        pass

    # 2. Format Excel baseline data
    excel_data = []
    for i, q in enumerate(excel_baseline_questions):
        q_text = q.get("question_text") if isinstance(q, dict) else str(q)
        q_cat = q.get("category", "General") if isinstance(q, dict) else "General"
        
        freq = 1
        if q_text in db_questions_data:
            freq, db_type = db_questions_data[q_text]
            if db_type == "DOMAIN":
                q_cat = "Domain"
            elif db_type == "GENERIC":
                q_cat = "General"
        
        excel_data.append({
            "question_text": q_text,
            "category": q_cat,
            "frequency": freq
        })

    # Initialize registry and PQ2
    system.initialize_system(excel_data)

    # 3. Populate PQ1 (Session Queue) with previous candidate questions
    # Note: These represent questions asked in previous interviews, so we use post_interview_update.
    # We map their question_id to match PQ2 if they exist there, to preserve global frequencies.
    # We also keep track of seen question texts to avoid generating duplicate IDs for the same question.
    formatted_prev = []
    seen_texts = {}  # maps q_text -> found_id
    for q in previous_candidates_questions:
        q_text = (q.get("question_text") or q.get("standardized_question") if isinstance(q, dict) else str(q)).strip()
        if not q_text:
            continue
        q_cat = q.get("category", "General") if isinstance(q, dict) else "General"

        if q_text in seen_texts:
            found_id = seen_texts[q_text]
        else:
            # Find matching question in PQ2 to reuse the ID and maintain correct frequency tracking
            found_id = None
            for q_id, priority, q_data in system.pq2.get_all_sorted():
                if q_data["question_text"] == q_text:
                    found_id = q_id
                    break

            if not found_id:
                found_id = f"prev_{uuid.uuid4().hex[:8]}"
                system.frequency_registry[found_id] = 0  # will be incremented to 1 in post_interview_update
            
            seen_texts[q_text] = found_id

        formatted_prev.append({
            "question_id": found_id,
            "question_text": q_text,
            "category": q_cat
        })

    # Load previous questions into PQ1 (increments frequency and registers them in PQ1)
    if formatted_prev:
        system.post_interview_update(formatted_prev)

    # 4. Determine target_count dynamically between 5 and 15
    # Growing by 3 questions per candidate in the session sequence
    target_count = max(5, min(15, len(previous_candidates_questions) + 3))

    # 5. Fetch questions using the new PQ-driven logic
    fetched_questions = system.fetch_interview_questions(target_count)

    # 6. Format response to match expected frontend structure
    prep_questions = []
    for q in fetched_questions:
        # Determine source (EXCEL_BASELINE or PREVIOUS_CANDIDATE)
        q_id = q["question_id"]
        is_prev = False
        for prev_q in formatted_prev:
            if prev_q["question_id"] == q_id:
                is_prev = True
                break
        
        source = "PREVIOUS_CANDIDATE" if is_prev else "EXCEL_BASELINE"
        prep_questions.append({
            "question_text": q["question_text"],
            "category": q["category"],
            "source": source
        })

    return {
        "agent_execution": "PROGRESSIVE_PREP_AGENT",
        "status": "SUCCESS",
        "data": {
            "candidate_name": candidate_name,
            "role_name": role_name,
            "prep_questions": prep_questions
        }
    }

def get_hr_panelist_for_role(role_name: str) -> str:
    """
    Parses Demands_Questions.xlsx and extracts the HR / Panelist name associated with the role.
    """
    excel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assests", "Demands_Questions.xlsx")
    if not os.path.exists(excel_path):
        return "Deepti Tiwari"
    
    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_path)
        if "Interview Question" not in wb.sheetnames:
            return "Deepti Tiwari"
        sheet = wb["Interview Question"]
        
        role_name_clean = role_name.strip().lower()
        is_ba = "ba" in role_name_clean or "analyst" in role_name_clean
        is_pmo = "pmo" in role_name_clean
        is_pm = ("pm" in role_name_clean or "manager" in role_name_clean) and not is_pmo
        
        for r in range(2, sheet.max_row + 1):
            panelist = sheet.cell(r, 1).value
            sheet_role = str(sheet.cell(r, 2).value or "").strip().lower()
            if not panelist or not sheet_role:
                continue
                
            matched = False
            if role_name_clean in sheet_role:
                matched = True
            elif is_pmo and "pmo" in sheet_role:
                matched = True
            elif is_ba and ("ba" in sheet_role or "analyst" in sheet_role) and not "pmo" in sheet_role:
                matched = True
            elif is_pm and ("pm" in sheet_role or "manager" in sheet_role) and not "pmo" in sheet_role:
                matched = True
                
            if matched:
                panelist_str = str(panelist).strip()
                if panelist_str and len(panelist_str) > 2 and not panelist_str.lower().startswith("panelist"):
                    return panelist_str
                    
        return "Deepti Tiwari"
    except Exception as e:
        return "Deepti Tiwari"

def strip_question_tags(text: str) -> str:
    """Aggressively strips leading bracketed or parenthesized tags and colons from the question text."""
    if not text:
        return ""
    import re
    cleaned = text.strip()
    prev = ""
    while cleaned != prev:
        prev = cleaned
        # Strip leading bracketed text
        cleaned = re.sub(r'^\[[^\]]+\]\s*', '', cleaned)
        # Strip leading parenthesized text
        cleaned = re.sub(r'^\([^\)]+\)\s*', '', cleaned)
        # Strip leading colons
        cleaned = re.sub(r'^:\s*', '', cleaned)
        cleaned = cleaned.strip()
    return cleaned

# -------------------------------------------------------------------
# SUB-AGENT 3: EMAIL_GENERATOR_AGENT
# -------------------------------------------------------------------
def run_email_generator_agent(
    action: str,
    candidate_name: str,
    candidate_email: str,
    role_name: str,
    prep_questions: list = None
) -> dict:
    if not action or action.upper() not in ["ACCEPT", "REJECT"]:
        return run_error_handler("MISSING_PARAMETER", "action must be either 'ACCEPT' or 'REJECT' for EMAIL_GENERATOR_AGENT.")
        
    if not candidate_name or not isinstance(candidate_name, str) or not candidate_name.strip():
        return run_error_handler("MISSING_PARAMETER", "candidate_name is required for EMAIL_GENERATOR_AGENT.")
        
    if not candidate_email or not isinstance(candidate_email, str) or not candidate_email.strip():
        return run_error_handler("MISSING_PARAMETER", "candidate_email is required for EMAIL_GENERATOR_AGENT.")
        
    if not role_name or not isinstance(role_name, str) or not role_name.strip():
        return run_error_handler("MISSING_PARAMETER", "role_name is required for EMAIL_GENERATOR_AGENT.")

    action = action.upper()
    prep_questions = prep_questions or []
    
    # Extract HR / Panelist name from Excel for this specific role
    hr_name = get_hr_panelist_for_role(role_name)

    # If ACCEPT action and prep_questions has fewer than 5 questions, automatically load at least 5 questions from Excel + LLM
    if action == "ACCEPT":
        if not prep_questions or len(prep_questions) < 5:
            try:
                prep_res = run_progressive_prep_agent(candidate_name, role_name, sequence_number=1)
                prep_questions = prep_res.get("data", {}).get("prep_questions", [])
            except Exception:
                pass
                
        if len(prep_questions) < 5:
            excel_qs = load_excel_questions_for_role(role_name)
            for q in excel_qs:
                if len(prep_questions) >= 5:
                    break
                prep_questions.append(q)

    questions_html = ""
    if action == "ACCEPT" and prep_questions:
        items = []
        for idx, q in enumerate(prep_questions[:15], start=1):
            if isinstance(q, dict):
                txt = q.get('question_text', '')
                txt_cleaned = strip_question_tags(txt)
                items.append(f"<li style='margin-bottom:8px; line-height:1.5;'>{txt_cleaned}</li>")
            else:
                txt_cleaned = strip_question_tags(str(q))
                items.append(f"<li style='margin-bottom:8px; line-height:1.5;'>{txt_cleaned}</li>")
        q_items = "".join(items)
        questions_html = f"""
        <div style="border:1px solid #002855; background-color:#001233; padding:16px; border-radius:8px; margin-top:16px; margin-bottom:16px;">
            <h3 style="color:#5fa8ff; margin-top:0; font-size:13px; border-b:1px solid #002855; padding-bottom:6px;">Client Interview Preparation Kit ({role_name})</h3>
            <ol style="color:#e2e8f0; font-size:12px; padding-left:18px; margin-bottom:0;">
                {q_items}
            </ol>
        </div>
        """

    sign_off_html = f"""
    <div style="margin-top:20px; border-t:1px solid #1e3d5f; padding-top:12px; font-size:12px; color:#cbd5e1;">
        <p style="margin-bottom:2px; font-weight:600;">Best regards,</p>
        <p style="margin:0; font-weight:700; color:#5fa8ff; font-size:13px;">{hr_name}</p>
        <p style="margin:0; font-weight:600; color:#94a3b8;">HR Recruitment Team</p>
        <p style="margin:0; color:#64748b; font-size:11px;">Protiviti Global Business Consulting</p>
    </div>
    """

    system_prompt = (
        "You are an expert HR Lead.\n"
        "Generate a professional, well-formatted email message for a candidate.\n"
        "Do NOT include any preparation kit questions or email signature/sign-off details in your response, as these are appended programmatically.\n"
        "Respond STRICTLY in JSON format with two keys: 'subject' (string) and 'body_html' (string).\n"
        "Do NOT include placeholders like [Your Name] or [Company Name]. Use 'Protiviti' for company name.\n"
        "Example:\n"
        "{\n"
        "  \"subject\": \"Application Update - Role\",\n"
        "  \"body_html\": \"<p>Dear Candidate...</p><p>We are pleased to inform you that you have been accepted...</p>\"\n"
        "}"
    )

    user_prompt = (
        f"Action: {action}\n"
        f"Candidate Name: {candidate_name}\n"
        f"Role Name: {role_name}\n"
        f"HR Recruiter Name: {hr_name}"
    )

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        res_content = execute_llm_request("general", messages=messages, response_format={"type": "json_object"})
        result = json.loads(res_content)
        body_html_content = result.get("body_html", "")
    except TokenExhaustionError:
        raise
    except Exception:
        body_html_content = ""

    if not body_html_content:
        if action == "ACCEPT":
            body_html_content = f"""
            <div style="font-family:sans-serif; color:#e2e8f0; line-height:1.6;">
                <p>Dear <strong>{candidate_name}</strong>,</p>
                <p>We are delighted to inform you that your profile has been selected for the position of <strong>{role_name}</strong> at Protiviti Global Business Consulting.</p>
                <p>To help you prepare effectively for the upcoming client interview sessions, our team has compiled a specialized technical and domain preparation kit based on past client evaluations for the {role_name} track:</p>
                {questions_html}
                <p>Please review these topics thoroughly. Our team will reach out shortly with schedule details.</p>
                {sign_off_html}
            </div>
            """
        else:
            body_html_content = f"""
            <div style="font-family:sans-serif; color:#e2e8f0; line-height:1.6;">
                <p>Dear <strong>{candidate_name}</strong>,</p>
                <p>Thank you for taking the time to apply for the position of <strong>{role_name}</strong> at Protiviti Global Business Consulting.</p>
                <p>After a thorough evaluation of your application and current project requirements, we regret to inform you that we will not be proceeding with your candidature for this specific role at this time.</p>
                <p>We truly appreciate your interest in our organization and wish you the best of luck in your professional journey.</p>
                {sign_off_html}
            </div>
            """
    else:
        # Clean up any duplicate signature generated by LLM to avoid duplicates
        import re
        body_html_content = re.sub(
            r'(?:Best regards|Regards|Sincerely|Warm regards),?\s*' + re.escape(hr_name) + r'.*$',
            '',
            body_html_content,
            flags=re.DOTALL | re.IGNORECASE
        ).strip()
        body_html_content = re.sub(
            r'(?:Best regards|Regards|Sincerely|Warm regards),?\s*(?:HR Team|Recruitment Team|HR Recruitment Team|Protiviti).*$',
            '',
            body_html_content,
            flags=re.DOTALL | re.IGNORECASE
        ).strip()
        
        # Clean up any duplicate questions block that LLM might have written
        body_html_content = re.sub(
            r'<div[^>]*>.*?Client Interview Preparation Kit.*?</div>',
            '',
            body_html_content,
            flags=re.DOTALL | re.IGNORECASE
        ).strip()

        # Append official ones exactly once
        if action == "ACCEPT" and questions_html:
            body_html_content += questions_html
        body_html_content += sign_off_html

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE candidates SET status = ? WHERE email = ?",
        (action.capitalize(), candidate_email)
    )
    conn.commit()
    conn.close()

    subject_str = result.get("subject") if (result and result.get("subject")) else (
        f"Congratulations! Selection Update for {role_name}" if action == "ACCEPT" else f"Update on Your Application for {role_name} Role"
    )

    return {
        "agent_execution": "EMAIL_GENERATOR_AGENT",
        "status": "SUCCESS",
        "email": {
            "to": candidate_email,
            "subject": subject_str,
            "body_html": body_html_content
        }
    }

# -------------------------------------------------------------------
# SUB-AGENT 4: FEEDBACK_STANDARDIZATION_AGENT
# -------------------------------------------------------------------
def run_feedback_standardization_agent(raw_feedback_text: str, session_id: str, candidate_id: str) -> dict:
    if not raw_feedback_text or not isinstance(raw_feedback_text, str) or not raw_feedback_text.strip() or len(raw_feedback_text.strip()) < 5:
        return run_error_handler("EMPTY_INPUT", "raw_feedback_text is empty, vague, or invalid for FEEDBACK_STANDARDIZATION_AGENT.")

    if not session_id:
        return run_error_handler("MISSING_PARAMETER", "session_id is required for FEEDBACK_STANDARDIZATION_AGENT.")

    if not candidate_id:
        return run_error_handler("MISSING_PARAMETER", "candidate_id is required for FEEDBACK_STANDARDIZATION_AGENT.")

    system_prompt = (
        "You are an expert interviewer assistant. Analyze the raw feedback text.\n"
        "If feedback is vague, invalid or contains zero interview detail, respond with error.\n"
        "Otherwise, extract distinct questions asked by client, clean up grammar, and classify each into category (Technical, Domain, Scenario, Behavioral).\n"
        "Respond strictly with JSON:\n"
        "{\n"
        "  \"status\": \"SUCCESS\" or \"ERROR\",\n"
        "  \"error_message\": \"reason if error else null\",\n"
        "  \"standardized_questions\": [\n"
        "    {\"question_text\": \"...\", \"category\": \"...\"}\n"
        "  ]\n"
        "}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": raw_feedback_text}
    ]
    res_content = execute_llm_request("general", messages=messages, response_format={"type": "json_object"})
    result = json.loads(res_content)

    if result.get("status") == "ERROR":
        return run_error_handler("EMPTY_INPUT", result.get("error_message", "Feedback input is vague or invalid."))

    standardized = result.get("standardized_questions", [])

    conn = get_db_connection()
    cursor = conn.cursor()
    for q in standardized:
        cursor.execute(
            "INSERT INTO session_questions (session_id, candidate_id, raw_text, standardized_question, category) VALUES (?, ?, ?, ?, ?)",
            (session_id, candidate_id, raw_feedback_text, q.get("question_text"), q.get("category"))
        )
    conn.commit()
    conn.close()

    return {
        "agent_execution": "FEEDBACK_STANDARDIZATION_AGENT",
        "status": "SUCCESS",
        "standardized_questions": standardized
    }

# -------------------------------------------------------------------
# SUB-AGENT 5: SESSION_CONSOLIDATION_AGENT
# -------------------------------------------------------------------
def run_session_consolidation_agent(session_questions: list, master_questions: list) -> dict:
    if session_questions is None or not isinstance(session_questions, list):
        return run_error_handler("INVALID_TYPE", "session_questions must be a list for SESSION_CONSOLIDATION_AGENT.")

    if master_questions is None or not isinstance(master_questions, list):
        return run_error_handler("INVALID_TYPE", "master_questions must be a list for SESSION_CONSOLIDATION_AGENT.")

    # Empty list defense
    if not session_questions:
        return {
            "agent_execution": "SESSION_CONSOLIDATION_AGENT",
            "status": "SUCCESS",
            "inserts": [],
            "updates": [],
            "database_updates": {"inserts": [], "updates": []},
            "pdf_structure": {"categories": []}
        }

    # Normalize text helper
    def normalize_text(text: str) -> str:
        return re.sub(r'[^a-z0-9]', '', str(text).lower()).strip()

    # Build a lookup of normalized master questions
    master_lookup = {} # normalized_text -> original_mq_dict
    for mq in master_questions:
        q_text = mq.get("question_text")
        if q_text:
            master_lookup[normalize_text(q_text)] = mq

    # Separate session questions into exact-matched and candidate-matched lists
    exact_updates = [] # list of {"question_text": ..., "increment_by": 1, "category": ...}
    unmatched_session_qs = []
    
    for sq in session_questions:
        sq_text = sq.get("question_text") or sq.get("standardized_question")
        if not sq_text:
            continue
        
        sq_norm = normalize_text(sq_text)
        if sq_norm in master_lookup:
            matched_mq = master_lookup[sq_norm]
            exact_updates.append({
                "question_text": matched_mq["question_text"],
                "increment_by": 1,
                "category": matched_mq.get("category") or matched_mq.get("type") or "GENERIC"
            })
        else:
            unmatched_session_qs.append(sq)

    # If all questions exact-match, we can bypass LLM entirely
    llm_inserts = []
    llm_updates = []
    
    if unmatched_session_qs:
        # We need LLM to search for semantic matches for unmatched questions
        # To avoid overloading the prompt, we filter master questions to only those with word overlap
        words = set()
        for sq in unmatched_session_qs:
            txt = sq.get("question_text") or sq.get("standardized_question") or ""
            for w in re.findall(r'\w+', txt.lower()):
                if len(w) > 3:
                    words.add(w)
                    
        filtered_master_qs = []
        for mq in master_questions:
            mq_text = mq.get("question_text") or ""
            mq_words = set(re.findall(r'\w+', mq_text.lower()))
            if mq_words.intersection(words):
                filtered_master_qs.append(mq)
                
        if len(filtered_master_qs) < 20:
            # Fallback to top frequency master questions
            sorted_mq = sorted(master_questions, key=lambda x: x.get("frequency_count") or x.get("frequency") or 1, reverse=True)
            filtered_master_qs = sorted_mq[:30]

        system_prompt = (
            "You are an expert consolidator.\n"
            "1. Identify and merge semantically equivalent questions between session_questions and master_questions.\n"
            "2. For matches with master_questions, calculate increment_by.\n"
            "3. For new unique questions, prepare inserts with initial_frequency = 1. The category MUST be strictly either 'GENERIC' (for general technical, scenario, or behavioral questions) or 'DOMAIN' (for role-specific or domain-specific questions). Under no circumstances should any other category name (such as 'General Questions', 'Technical', 'General') be used in the inserts category/type field.\n"
            "4. Organize all questions into structured categories for pdf_structure. You MUST group them into exactly two category blocks: 'General Questions' and 'Domain Questions'.\n"
            "Respond strictly with JSON:\n"
            "{\n"
            "  \"database_updates\": {\n"
            "    \"inserts\": [\n"
            "      {\"question_text\": \"...\", \"category\": \"GENERIC or DOMAIN\", \"initial_frequency\": 1}\n"
            "    ],\n"
            "    \"updates\": [\n"
            "      {\"question_text\": \"...\", \"increment_by\": 1}\n"
            "    ]\n"
            "  },\n"
            "  \"pdf_structure\": {\n"
            "    \"categories\": [\n"
            "      {\n"
            "        \"category_name\": \"General Questions\",\n"
            "        \"questions\": [\"...\"]\n"
            "      },\n"
            "      {\n"
            "        \"category_name\": \"Domain Questions\",\n"
            "        \"questions\": [\"...\"]\n"
            "      }\n"
            "    ]\n"
            "  }\n"
            "}"
        )

        user_prompt = (
            f"Session Questions: {json.dumps(unmatched_session_qs)}\n\n"
            f"Master Questions: {json.dumps(filtered_master_qs)}"
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            res_content = execute_llm_request("general", messages=messages, response_format={"type": "json_object"})
            result = json.loads(res_content)
            
            db_updates = result.get("database_updates", {"inserts": [], "updates": []})
            llm_inserts = db_updates.get("inserts", [])
            llm_updates = db_updates.get("updates", [])
        except TokenExhaustionError:
            raise
        except Exception as e:
            print(f"Error in run_session_consolidation_agent (LLM/JSON parsing): {e}")
            # If LLM fails, treat unmatched questions as inserts
            for sq in unmatched_session_qs:
                sq_text = sq.get("question_text") or sq.get("standardized_question")
                sq_cat = sq.get("category", "GENERIC")
                norm_cat = "DOMAIN" if "domain" in str(sq_cat).lower() else "GENERIC"
                llm_inserts.append({
                    "question_text": sq_text,
                    "category": norm_cat,
                    "initial_frequency": 1
                })

    # Merge database updates
    final_inserts = llm_inserts
    
    # Merge updates (combine exact_updates and llm_updates)
    merged_updates = {} # question_text -> increment_by
    for up in exact_updates:
        q_text = up["question_text"]
        merged_updates[q_text] = merged_updates.get(q_text, 0) + up["increment_by"]
        
    for up in llm_updates:
        q_text = up.get("question_text")
        if q_text:
            merged_updates[q_text] = merged_updates.get(q_text, 0) + up.get("increment_by", 1)
            
    final_updates = [{"question_text": k, "increment_by": v} for k, v in merged_updates.items()]

    # Reconstruct pdf_structure categories deterministically in Python
    # This guarantees that categorization is always clean and matches what is saved!
    general_questions_set = set()
    domain_questions_set = set()
    
    # 1. Add from exact updates
    for up in exact_updates:
        q_text = up["question_text"]
        q_cat = up["category"]
        if "domain" in str(q_cat).lower():
            domain_questions_set.add(q_text)
        else:
            general_questions_set.add(q_text)
            
    # 2. Add from LLM updates (retrieve their category from master questions map)
    master_cat_map = {mq["question_text"]: (mq.get("category") or mq.get("type") or "GENERIC") for mq in master_questions if mq.get("question_text")}
    for up in llm_updates:
        q_text = up.get("question_text")
        if q_text:
            q_cat = master_cat_map.get(q_text, "GENERIC")
            if "domain" in str(q_cat).lower():
                domain_questions_set.add(q_text)
            else:
                general_questions_set.add(q_text)
                
    # 3. Add from LLM inserts
    for ins in llm_inserts:
        q_text = ins.get("question_text")
        q_cat = ins.get("category", "GENERIC")
        if q_text:
            if "domain" in str(q_cat).lower():
                domain_questions_set.add(q_text)
            else:
                general_questions_set.add(q_text)

    # Convert sets to sorted lists to keep stable order
    pdf_struct = {
        "categories": [
            {
                "category_name": "General Questions",
                "category": "General Questions",
                "name": "General Questions",
                "questions": sorted(list(general_questions_set))
            },
            {
                "category_name": "Domain Questions",
                "category": "Domain Questions",
                "name": "Domain Questions",
                "questions": sorted(list(domain_questions_set))
            }
        ]
    }

    db_updates = {
        "inserts": final_inserts,
        "updates": final_updates
    }

    conn = get_db_connection()
    cursor = conn.cursor()

    for item in final_inserts:
        q_text = item.get("question_text")
        if not q_text or not isinstance(q_text, str):
            continue
        cat = item.get("category", "GENERIC")
        q_type = "DOMAIN" if "domain" in cat.lower() else "GENERIC"
        freq = item.get("initial_frequency", 1)
        
        cursor.execute(
            """INSERT INTO master_questions (question_text, type, frequency)
               VALUES (?, ?, ?)
               ON CONFLICT (question_text) 
               DO UPDATE SET 
                   frequency = frequency + ?, 
                   type = excluded.type""",
            (q_text, q_type, freq, freq)
        )

    for item in final_updates:
        q_text = item.get("question_text")
        if not q_text or not isinstance(q_text, str):
            continue
        inc = item.get("increment_by", 1)
        cursor.execute(
            "UPDATE master_questions SET frequency = frequency + ? WHERE question_text = ?",
            (inc, q_text)
        )

    conn.commit()
    conn.close()

    return {
        "agent_execution": "SESSION_CONSOLIDATION_AGENT",
        "status": "SUCCESS",
        "inserts": final_inserts,
        "updates": final_updates,
        "database_updates": db_updates,
        "pdf_structure": pdf_struct
    }

# -------------------------------------------------------------------
# SUB-AGENT 6: ROLE_ALIGNMENT_AGENT
# -------------------------------------------------------------------
ROLE_ALIGNMENT_LIST = [
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
    "UK  Generic BA",
    "Asset Management",
    "CCT - Conversation Banking",
    "Gen AI Automation BA",
]

def run_role_alignment_agent(candidate_name: str, resume_text: str, sme_feedback: str = "") -> dict:
    if not candidate_name or not candidate_name.strip():
        return run_error_handler("MISSING_PARAMETER", "candidate_name is required for ROLE_ALIGNMENT_AGENT.")
    if not resume_text or not resume_text.strip():
        return run_error_handler("MISSING_PARAMETER", "resume_text is required for ROLE_ALIGNMENT_AGENT.")

    roles_str = "\n".join(f'{i+1}. "{r}"' for i, r in enumerate(ROLE_ALIGNMENT_LIST))

    system_prompt = (
        "You are the Role Alignment Agent for Protiviti's Hiring Pipeline.\n"
        "Analyze an accepted candidate's profile and match them to the top 3 to 4 best predefined target roles from the list below.\n\n"
        "PREDEFINED TARGET ROLES (you MUST select only from this list, verbatim):\n"
        f"{roles_str}\n\n"
        "ROLE MATCHING LOGIC:\n"
        "- FX/Payments/Accounts: SWIFT, SEPA, Fedwire, FX trading, settlement, treasury\n"
        "  -> Ops-heavy: 'Transaction Banking (Payments BA - Ops specialization)' or 'PaymentsOps BA'\n"
        "  -> US hours/location: 'Accounts BA (US Timezone)'\n"
        "- French fluency: 'Asset Management (French speaking BA)'\n"
        "- UK regulations (FCA, UK banking): look for UK-specific roles; if none fit, 'UK  Generic BA'\n"
        "- South Asia geography: 'South Asia BA'\n"
        "- Lending: credit risk, mortgages, loans, origination, debt recovery\n"
        "- Analytics/Data: SQL, Python, Tableau, data modeling, ETL\n"
        "- Fraud: AML, KYC, fraud detection, collections, risk systems\n"
        "- CCT/Digital: omni-channel, mobile banking, IVR, chatbots, contact center\n"
        "- Gen AI: LLM integration, prompt engineering, agentic workflows, AI automation\n\n"
        "Respond STRICTLY with JSON containing a 'matches' array of 3 to 4 best roles:\n"
        "{\n"
        "  \"matches\": [\n"
        "    {\n"
        "      \"role\": \"EXACT role string from the predefined list above\",\n"
        "      \"score\": 0-100,\n"
        "      \"reason\": \"concise explanation matching details of the candidate to this role\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    user_prompt = (
        f"Candidate Name: {candidate_name}\n"
        f"Resume Text: {resume_text}\n"
        f"SME Interview Feedback: {sme_feedback or 'Not provided'}"
    )

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        res_content = execute_llm_request("general", messages=messages, response_format={"type": "json_object"})
        result = json.loads(res_content)
        
        matches = result.get("matches", [])
        if not isinstance(matches, list):
            matches = []

        validated_matches = []
        for m in matches:
            role = m.get("role", "")
            score = m.get("score", 0)
            reason = m.get("reason", "")

            # Validate role
            if role not in ROLE_ALIGNMENT_LIST:
                # Fuzzy fallback: pick closest by word overlap
                best, best_score = ROLE_ALIGNMENT_LIST[0], 0
                matched_words = set(role.lower().split())
                for allowed_role in ROLE_ALIGNMENT_LIST:
                    intersection_score = len(set(allowed_role.lower().split()) & matched_words)
                    if intersection_score > best_score:
                        best_score, best = intersection_score, allowed_role
                role = best
            
            validated_matches.append({
                "role": role,
                "score": int(score) if str(score).isdigit() else 0,
                "reason": str(reason)
            })

        # Keep top 3-4 matches sorted by score descending
        validated_matches.sort(key=lambda x: x["score"], reverse=True)
        final_matches = validated_matches[:4]

        return {
            "agent_execution": "ROLE_ALIGNMENT_AGENT",
            "status": "SUCCESS",
            "matches": final_matches
        }
    except TokenExhaustionError:
        raise
    except Exception as e:
        return run_error_handler("LLM_ERROR", f"Role alignment failed: {str(e)}")


# Backward compatibility wrappers
def run_resume_evaluation(resume_text: str, job_description: str) -> dict:
    if not resume_text or not job_description:
        return run_error_handler("MISSING_PARAMETER", "resume_text and job_description are required.")
    system_prompt = (
        "Evaluate resume against JD. Respond strictly with JSON:\n"
        "{\"overall_match_score\": 85, \"status\": \"Shortlist\", \"reasoning\": \"...\", \"sme_questions\": []}"
    )
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Resume:\n{resume_text}\nJD:\n{job_description}"}]
    res_content = execute_llm_request("general", messages=messages, response_format={"type": "json_object"})
    res = json.loads(res_content)
    return {"operation": "RESUME_EVALUATION", **res}

def run_email_generation(*args, **kwargs):
    res = run_email_generator_agent(*args, **kwargs)
    if isinstance(res, dict) and "email" in res:
        res["to"] = res["email"].get("to")
        res["subject"] = res["email"].get("subject")
        res["email_body_html"] = res["email"].get("body_html")
        res["body_html"] = res["email"].get("body_html")
    return res

def run_feedback_standardization(*args, **kwargs):
    return run_feedback_standardization_agent(*args, **kwargs)

def run_progressive_prep_assembly(historical_questions, current_session_questions):
    return run_progressive_prep_agent(
        candidate_name="Candidate",
        role_name="Software Engineer",
        sequence_number=1,
        excel_baseline_questions=historical_questions,
        previous_candidates_questions=current_session_questions
    )

def run_final_consolidation(all_session_questions, master_questions):
    return run_session_consolidation_agent(all_session_questions, master_questions)
