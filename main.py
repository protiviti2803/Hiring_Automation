import os
import sys
import time
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import ollama

app = FastAPI(title="HR AI Recruitment Portal")

# Auto-start Ollama if it's shut down
def ensure_ollama_is_running():
    try:
        ollama.list()
    except Exception:
        print("⚙️ Starting Ollama service automatically...")
        if sys.platform == "win32":
            subprocess.Popen(["cmd", "/c", "start", "/B", "ollama", "serve"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(4)

ensure_ollama_is_running()

# Mount the 'static' folder to serve HTML/CSS/JS assets
app.mount("/static", StaticFiles(directory="static"), name="static")

# Data format structure for receiving user web prompts
class DemandRequest(BaseModel):
    demands: str

@app.get("/")
def read_root():
    # Serves the main UI page when you visit http://127.0.0.1:8000
    return FileResponse(os.path.join("static", "index.html"))

@app.post("/generate")
def generate_jd(data: DemandRequest):
    if not data.demands.strip():
        raise HTTPException(status_code=400, detail="Demands payload cannot be empty")
    
    try:
        # Request data from your custom local Ollama model
        response = ollama.generate(
            model='jd-generator',
            prompt=data.demands,
            stream=False # Keep false for stable payload delivery to the web UI
        )
        return {"response": response['response']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))