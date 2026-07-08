import os
import json
import httpx
from groq import AsyncGroq

async def compare_cv_with_jd_async(cv_text: str, jd_text: str, api_key: str, provider: str = "groq") -> dict:
    """
    Performs a direct semantic comparison between CV and JD using Groq or local Ollama.
    Returns a parsed JSON dictionary.
    """
    system_prompt = (
        "You are an expert technical recruiter and talent acquisition specialist.\n"
        "Your task is to perform a detailed semantic comparison between a candidate's resume (CV) and a Job Description (JD).\n"
        "Evaluate the match quality across multiple dimensions.\n\n"
        "You MUST respond strictly with a JSON object. Do not include any conversational filler, markdown codeblocks (like ```json), or text outside the JSON object.\n\n"
        "The JSON structure must match this schema:\n"
        "{\n"
        "  \"overall_score\": 85,\n"
        "  \"skills_analysis\": {\n"
        "    \"matching_skills\": [\"Python\", \"FastAPI\"],\n"
        "    \"missing_skills\": [\"Kubernetes\"],\n"
        "    \"optional_skills\": [\"AWS\"]\n"
        "  },\n"
        "  \"experience_alignment\": \"description of alignment\",\n"
        "  \"strengths\": [\"strength 1\", \"strength 2\"],\n"
        "  \"gaps\": [\"gap 1\", \"gap 2\"],\n"
        "  \"recommendation\": {\n"
        "    \"status\": \"Shortlist | Interview | Reject\",\n"
        "    \"reasoning\": \"detailed explanation\"\n"
        "  }\n"
        "}"
    )
    
    user_prompt = (
        f"Candidate Resume (CV) Content:\n"
        f"\"\"\"\n{cv_text}\n\"\"\"\n\n"
        f"Job Description (JD) Content:\n"
        f"\"\"\"\n{jd_text}\n\"\"\"\n"
    )
    
    if provider.lower() == "ollama":
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": "mistral",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "stream": False,
                        "format": "json"
                    }
                )
                if response.status_code != 200:
                    raise Exception(f"Ollama local service returned status code {response.status_code}")
                result_json = response.json()
                content = result_json["message"]["content"]
                return json.loads(content)
            except Exception as e:
                raise Exception(f"Local Ollama Matcher Error: {str(e)}. Make sure Ollama is running and has model 'mistral' installed.")

    # Default to Groq Llama 3.3
    if not api_key or api_key == "GROQ_API_KEY":
        raise ValueError("Groq API Key is required for CV/JD matching.")
        
    client = AsyncGroq(api_key=api_key)
    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content)
    except Exception as e:
        raise Exception(f"Groq API Error: {str(e)}")
