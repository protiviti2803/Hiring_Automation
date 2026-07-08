import os
import sys
import time
import subprocess
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
from app.services.parser import extract_text_from_pdf
from app.services.matcher import compare_cv_with_jd_async
from app.core.database import init_db
from app.services.db_service import save_demand_and_jd, extract_keywords, get_all_history, get_demand_and_jd_by_id

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load environment variables from the .env file in the root directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(BASE_DIR), ".env"))

app = FastAPI(title="HR AI Recruitment Portal")

@app.on_event("startup")
def startup_event():
    init_db()
MODEL_NAME = "mistral"  # Replace with your custom model name if different
SYSTEM_PROMPT = """ You are an expert HR and Technical Recruiter. Your sole task is to generate professional, well-structured Job Descriptions (JDs) based on client demands.
 
When the user gives you demands, immediately output a JD with these sections:
1. Job Title (extrapolated from demands)
2. Role Overview
3. Key Responsibilities (bullet points)
4. Required Skills & Qualifications (must-haves vs nice-to-haves)
5. Preferred Experience
 
Keep the tone professional, attractive to candidates, and highly organized. Do not add conversational filler before or after the JD.
"""


# Ollama service check removed as generation relies solely on Groq

# Mount the 'static' folder to serve HTML/CSS/JS assets
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/assests", StaticFiles(directory=os.path.join(BASE_DIR, "assests")), name="assests")

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "GROQ_API_KEY":
        raise HTTPException(
            status_code=400, 
            detail="GROQ_API_KEY"
        )
    return Groq(api_key=api_key)

def generate_jd_with_groq(prompt: str) -> str:
    client = get_groq_client()
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        raise Exception(f"Groq API Error: {str(e)}")

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
        # Extract keywords
        keywords_list = extract_keywords(data.demands, response_text)
        # Save to database and retrieve ID
        inserted_id = save_demand_and_jd(data.demands, response_text, keywords_list)
        return {
            "response": response_text,
            "id": inserted_id,
            "keywords": keywords_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.post("/api/compare-upload")
async def compare_upload(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
    provider: str = Form("groq")
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    os.makedirs("data", exist_ok=True)
    temp_path = "data/temp_upload.pdf"
    
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temporary file: {str(e)}")
        
    try:
        cv_text = extract_text_from_pdf(temp_path)
        if not cv_text.strip() or cv_text.startswith("Error"):
            raise ValueError(cv_text or "Failed to parse text from the PDF file.")
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=400, detail=f"Error reading PDF resume: {str(e)}")
        
    try:
        api_key = os.getenv("GROQ_API_KEY")
        result = await compare_cv_with_jd_async(cv_text, jd_text, api_key, provider)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass