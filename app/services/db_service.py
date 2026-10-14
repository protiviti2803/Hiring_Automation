import os
import re
import json
import sqlite3
from openai import OpenAI
from app.core.database import get_db_connection

def extract_keywords(demands: str, jd_text: str) -> list:
    """
    Extracts key technical keywords from client demands and the generated JD.
    Attempts to use the GPT_OSS_20B API first; falls back to local regex-based matching if offline/error.
    """
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GPT_OSS_20B") or os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            base_url = os.getenv("GPT_OSS_20B_BASE_URL") or os.getenv("GROQ_API_BASE_URL") or "https://api.groq.com/openai/v1"
            client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            prompt = (
                f"Identify the key technical skills, programming languages, tools, frameworks, cloud services, or databases "
                f"mentioned in the following text. Respond strictly with a JSON list of strings, e.g. [\"Python\", \"FastAPI\", \"SQL\"]. "
                f"Do not include any conversational filler, markdown formatting (like ```json), or text outside the JSON list.\n\n"
                f"Demands: {demands}\n\n"
                f"Job Description:\n{jd_text}"
            )
            model_id = os.getenv("GPT_OSS_20B_MODEL_ID", "openai/gpt-oss-120b")
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=model_id,
            )
            content = chat_completion.choices[0].message.content.strip()
            # Clean possible markdown wrap just in case
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("\n", 1)[0]
            content = content.strip()
            
            data = json.loads(content)
            if isinstance(data, list):
                return [str(item).strip() for item in data]
            elif isinstance(data, dict):
                # Sometimes LLM might wrap in a dict key like "keywords" or "skills"
                for val in data.values():
                    if isinstance(val, list):
                        return [str(item).strip() for item in val]
        except Exception:
            # Fallback to local regex-based parsing
            pass

    # Local Fallback Matcher
    tech_keywords = [
        "python", "javascript", "typescript", "java", "c++", "c#", "ruby", "php", "go", "golang", "rust", "scala", "kotlin", "swift",
        "html", "css", "sql", "nosql", "mysql", "postgresql", "mongodb", "sqlite", "oracle", "redis", "cassandra",
        "react", "angular", "vue", "next.js", "nuxt", "svelte", "django", "flask", "fastapi", "spring", "express", "laravel",
        "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins", "git", "ci/cd", "devops",
        "machine learning", "ml", "deep learning", "dl", "nlp", "llm", "data science", "pytorch", "tensorflow", "keras", "scikit-learn",
        "spark", "hadoop", "pandas", "numpy", "powerbi", "tableau", "rest api", "graphql", "microservices", "agile", "scrum"
    ]
    
    text_to_search = f"{demands} {jd_text}".lower()
    found = []
    
    display_map = {
        "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript", "java": "Java", 
        "c++": "C++", "c#": "C#", "ruby": "Ruby", "php": "PHP", "go": "Go", "golang": "Go", 
        "rust": "Rust", "scala": "Scala", "kotlin": "Kotlin", "swift": "Swift", "html": "HTML", 
        "css": "CSS", "sql": "SQL", "nosql": "NoSQL", "mysql": "MySQL", "postgresql": "PostgreSQL", 
        "mongodb": "MongoDB", "sqlite": "SQLite", "oracle": "Oracle", "redis": "Redis", 
        "cassandra": "Cassandra", "react": "React", "angular": "Angular", "vue": "Vue", 
        "next.js": "Next.js", "nuxt": "Nuxt", "svelte": "Svelte", "django": "Django", 
        "flask": "Flask", "fastapi": "FastAPI", "spring": "Spring", "express": "Express", 
        "laravel": "Laravel", "aws": "AWS", "azure": "Azure", "gcp": "GCP", "docker": "Docker", 
        "kubernetes": "Kubernetes", "k8s": "Kubernetes", "terraform": "Terraform", "ansible": "Ansible", 
        "jenkins": "Jenkins", "git": "Git", "ci/cd": "CI/CD", "devops": "DevOps", 
        "machine learning": "Machine Learning", "ml": "Machine Learning", "deep learning": "Deep Learning", 
        "dl": "Deep Learning", "nlp": "NLP", "llm": "LLM", "data science": "Data Science", 
        "pytorch": "PyTorch", "tensorflow": "TensorFlow", "keras": "Keras", "scikit-learn": "Scikit-Learn", 
        "spark": "Spark", "hadoop": "Hadoop", "pandas": "Pandas", "numpy": "NumPy", 
        "powerbi": "Power BI", "tableau": "Tableau", "rest api": "REST API", "graphql": "GraphQL", 
        "microservices": "Microservices", "agile": "Agile", "scrum": "Scrum"
    }
    
    for kw in tech_keywords:
        escaped_kw = re.escape(kw)
        if kw.endswith(('++', '#')):
            pattern = rf"\b{escaped_kw}(?!\w)"
        else:
            pattern = rf"\b{escaped_kw}\b"
            
        if re.search(pattern, text_to_search):
            display_name = display_map.get(kw, kw.capitalize())
            if display_name not in found:
                found.append(display_name)
                
    return found

def save_demand_and_jd(demand_text: str, jd_text: str, keywords: list) -> int:
    """
    Accepts keywords as a list of strings, serializes it to a comma-separated string,
    and performs an SQL INSERT to save demands, generated_JD, and keywords.
    Commits the transaction and returns the inserted row's ID.
    """
    serialized_keywords = ", ".join(keywords)
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO client_demands (demands, generated_JD, keywords) VALUES (?, ?, ?)",
            (demand_text, jd_text, serialized_keywords)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_demand_and_jd_by_id(record_id: int) -> dict:
    """
    Fetches the record from the database by ID and reconstructs the data into
    a Python dictionary structure.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT demands, generated_JD, keywords FROM client_demands WHERE id = ?",
            (record_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "demand": row["demands"],
            "JD": row["generated_JD"],
            "keywords": [k.strip() for k in row["keywords"].split(",")] if row["keywords"] else []
        }
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_all_history() -> list:
    """
    Retrieves id, preview of demands, extracted title, and created_at for all records
    sorted by created_at DESC.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, demands, generated_JD, created_at FROM client_demands ORDER BY created_at DESC")
        rows = cursor.fetchall()
        history = []
        for row in rows:
            # First 100 characters of demands
            demands_preview = row["demands"][:100]
            
            # First line of generated_JD to act as the job title
            generated_jd = row["generated_JD"]
            if generated_jd and ("overall_score" in generated_jd or "overallscore" in generated_jd):
                continue
                
            first_line = ""
            if generated_jd:
                lines = [l.strip() for l in generated_jd.split("\n") if l.strip()]
                if lines:
                    first_line = lines[0]
            
            # Clean up potential markdown formatting from first line like "# Job Title" or "**Job Title**"
            first_line_clean = re.sub(r'[*#_`\-]', '', first_line).strip()
            # If it starts with "1. Job Title:" or similar, clean it
            if first_line_clean.lower().startswith("job title:"):
                first_line_clean = first_line_clean[len("job title:"):].strip()
            elif first_line_clean.lower().startswith("1. job title:"):
                first_line_clean = first_line_clean[len("1. job title:"):].strip()
            
            # Clean trailing colons and extra whitespace
            first_line_clean = first_line_clean.rstrip(':').strip()
            
            history.append({
                "id": row["id"],
                "demands": demands_preview,
                "title": first_line_clean or "Job Description Report",
                "created_at": row["created_at"]
            })
        return history
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def save_client_feedback(original_demand: str, raw_feedback: str, categories: dict, reasoning: str = "", candidate_name: str = "", role: str = "") -> int:
    """
    Persists a client feedback record with its LLM-categorized keyword buckets.
    `categories` is a dict with keys hard_skills, soft_skills, domain_knowledge, behavioral_knowledge (each a list).
    Returns the inserted row id.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO client_feedbacks
               (original_demand, raw_feedback, candidate_name, role, hard_skills, soft_skills,
                domain_knowledge, behavioral_knowledge, reasoning)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                original_demand,
                raw_feedback,
                candidate_name,
                role,
                json.dumps(categories.get("hard_skills", [])),
                json.dumps(categories.get("soft_skills", [])),
                json.dumps(categories.get("domain_knowledge", [])),
                json.dumps(categories.get("behavioral_knowledge", [])),
                reasoning
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_all_client_feedbacks() -> list:
    """Returns all client feedback records (most recent first) with keyword lists deserialized."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, original_demand, raw_feedback, candidate_name, role, hard_skills, soft_skills,
                      domain_knowledge, behavioral_knowledge, reasoning, created_at
               FROM client_feedbacks
               ORDER BY created_at DESC"""
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "original_demand": row["original_demand"],
                "raw_feedback": row["raw_feedback"],
                "candidate_name": row["candidate_name"] if "candidate_name" in row.keys() else "",
                "role": row["role"] if "role" in row.keys() else "",
                "hard_skills": json.loads(row["hard_skills"] or "[]"),
                "soft_skills": json.loads(row["soft_skills"] or "[]"),
                "domain_knowledge": json.loads(row["domain_knowledge"] or "[]"),
                "behavioral_knowledge": json.loads(row["behavioral_knowledge"] or "[]"),
                "reasoning": row["reasoning"],
                "created_at": row["created_at"]
            })
        return result
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_all_feedback_keywords() -> dict:
    """
    Aggregates every stored feedback's keywords into one deduplicated dict of
    {hard_skills, soft_skills, domain_knowledge, behavioral_knowledge}.
    Used to augment CV screening.
    """
    feedbacks = get_all_client_feedbacks()
    buckets = {"hard_skills": [], "soft_skills": [], "domain_knowledge": [], "behavioral_knowledge": []}
    seen = {k: set() for k in buckets}
    for fb in feedbacks:
        for key in buckets:
            for item in fb.get(key, []):
                low = str(item).strip().lower()
                if low and low not in seen[key]:
                    seen[key].add(low)
                    buckets[key].append(item)
    return buckets


def save_to_master_db(question_text: str, type: str):
    """
    Saves a question to the master database. 
    If a conflict occurs on question_text (the question already exists),
    it automatically increments the frequency by 1.
    """
    if type not in ('GENERIC', 'DOMAIN'):
        raise ValueError("Type must be either 'GENERIC' or 'DOMAIN'")
        
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO master_questions (question_text, type, frequency)
               VALUES (?, ?, 1)
               ON CONFLICT (question_text) 
               DO UPDATE SET 
                   frequency = frequency + 1,
                   type = excluded.type;""",
            (question_text, type)
        )
        conn.commit()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def load_active_queues() -> dict:
    """
    Fetches data needed to populate the runtime priority queues:
      - PQ_Generic Data: Fetch questions where type = 'GENERIC', ordered by frequency DESC, with strict LIMIT 5.
      - PQ_Domain Data: Fetch questions where type = 'DOMAIN', ordered by frequency DESC (no limit).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch generic questions (LIMIT 5)
        cursor.execute(
            """SELECT id, question_text, type, frequency 
               FROM master_questions 
               WHERE type = 'GENERIC' 
               ORDER BY frequency DESC 
               LIMIT 5"""
        )
        generic_rows = cursor.fetchall()
        generic_data = [dict(row) for row in generic_rows]
        
        # Fetch domain questions (no limit)
        cursor.execute(
            """SELECT id, question_text, type, frequency 
               FROM master_questions 
               WHERE type = 'DOMAIN' 
               ORDER BY frequency DESC"""
        )
        domain_rows = cursor.fetchall()
        domain_data = [dict(row) for row in domain_rows]
        
        return {
            "PQ_Generic": generic_data,
            "PQ_Domain": domain_data
        }
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def delete_client_demand_by_id(record_id: int) -> bool:
    """
    Permanently deletes a client demand record from the database by its ID.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM client_demands WHERE id = ?", (record_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

