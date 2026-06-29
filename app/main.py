import os
import sys
import time
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load environment variables from the .env file in the root directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(BASE_DIR), ".env"))

app = FastAPI(title="HR AI Recruitment Portal")
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
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))