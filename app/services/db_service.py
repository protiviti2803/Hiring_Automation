import os
import re
import json
import sqlite3
from groq import Groq
from app.core.database import get_db_connection

def extract_keywords(demands: str, jd_text: str) -> list:
    """
    Extracts key technical keywords from client demands and the generated JD.
    Attempts to use the Groq API first; falls back to local regex-based matching if offline/error.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key != "GROQ_API_KEY":
        try:
            client = Groq(api_key=api_key)
            prompt = (
                f"Identify the key technical skills, programming languages, tools, frameworks, cloud services, or databases "
                f"mentioned in the following text. Respond strictly with a JSON list of strings, e.g. [\"Python\", \"FastAPI\", \"SQL\"]. "
                f"Do not include any conversational filler, markdown formatting (like ```json), or text outside the JSON list.\n\n"
                f"Demands: {demands}\n\n"
                f"Job Description:\n{jd_text}"
            )
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama-3.1-8b-instant",
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

