import os
import json
import httpx
from openai import AsyncOpenAI
from app.core.llm_client import TokenExhaustionError, execute_llm_request_async
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def cosine_keyword_prefilter(cv_text: str, keywords: list, threshold: float = 0.08) -> dict:
    """
    LAYER 1 (token optimization): cheap cosine-similarity pre-filter.

    For each HR-provided keyword, measure how strongly it already appears in the CV
    using TF-IDF cosine similarity between the keyword and the CV text. Keywords whose
    similarity is >= threshold are treated as "likely present"; the rest are "likely
    missing". This coarse signal is handed to the deep LLM pass so the model can focus
    its reasoning (and avoids us needing a separate expensive LLM call per keyword).

    Returns:
      {
        "likely_present": [{"keyword": str, "score": float}, ...],
        "likely_missing": [{"keyword": str, "score": float}, ...]
      }
    """
    clean_keywords = [k.strip() for k in keywords if k and k.strip()]
    result = {"likely_present": [], "likely_missing": []}
    if not clean_keywords or not cv_text or not cv_text.strip():
        # Nothing to compare -> everything is "missing" (unknown) so the LLM checks all.
        result["likely_missing"] = [{"keyword": k, "score": 0.0} for k in clean_keywords]
        return result

    try:
        corpus = [cv_text] + clean_keywords
        vectorizer = TfidfVectorizer(stop_words="english", min_df=1, ngram_range=(1, 2))
        tfidf = vectorizer.fit_transform(corpus)
        sims = cosine_similarity(tfidf[0], tfidf[1:]).flatten()
    except Exception:
        sims = [0.0] * len(clean_keywords)

    for kw, sim in zip(clean_keywords, sims):
        entry = {"keyword": kw, "score": round(float(sim), 4)}
        if sim >= threshold:
            result["likely_present"].append(entry)
        else:
            result["likely_missing"].append(entry)
    return result


async def compare_cv_with_jd_async(cv_text: str, jd_text: str, api_key: str, provider: str = "groq", missing_keywords: list = None) -> dict:
    """
    Performs a direct semantic comparison between CV and JD using Groq or local Ollama.
    Returns a parsed JSON dictionary.

    Two-layer keyword screening when `missing_keywords` is provided:
      Layer 1 - cosine_keyword_prefilter() pre-classifies each keyword as likely
                present/missing in the CV (cheap, no LLM tokens).
      Layer 2 - this LLM call does the deep semantic verification, using the Layer 1
                signal as a hint, and returns a keyword_alignment section.
    """
    missing_keywords = [k.strip() for k in (missing_keywords or []) if k and k.strip()]

    # LAYER 1: cosine pre-filter
    prefilter = cosine_keyword_prefilter(cv_text, missing_keywords) if missing_keywords else None

    keyword_schema = ""
    keyword_block = ""
    if missing_keywords:
        keyword_schema = (
            "  \"keyword_alignment\": {\n"
            "    \"matched_keywords\": [\"keyword actually evidenced in the CV\"],\n"
            "    \"missing_keywords\": [\"keyword not evidenced in the CV\"],\n"
            "    \"keyword_match_ratio\": 0.0\n"
            "  },\n"
        )
        present_hint = ", ".join(k["keyword"] for k in prefilter["likely_present"]) or "none"
        missing_hint = ", ".join(k["keyword"] for k in prefilter["likely_missing"]) or "none"
        keyword_block = (
            f"\n\nADDITIONAL REQUIRED KEYWORDS (provided by HR — the candidate MUST be screened against these too):\n"
            f"{', '.join(missing_keywords)}\n\n"
            f"Layer-1 cosine pre-screen hint (verify with your own judgement, do not blindly trust):\n"
            f"- Likely already present in CV: {present_hint}\n"
            f"- Likely missing from CV: {missing_hint}\n\n"
            f"Populate the keyword_alignment section: confirm which keywords are genuinely evidenced in the CV "
            f"(matched_keywords) versus absent (missing_keywords), and set keyword_match_ratio = matched / total keywords. "
            f"Weigh these keywords into the overall_score and recommendation — a candidate weak on the required "
            f"keywords should score lower."
        )

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
        f"{keyword_schema}"
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
        f"{keyword_block}"
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
                parsed = json.loads(content)
                if prefilter is not None:
                    parsed["keyword_prefilter"] = prefilter
                return parsed
            except Exception as e:
                raise Exception(f"Local Ollama Matcher Error: {str(e)}. Make sure Ollama is running and has model 'mistral' installed.")

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response_content = await execute_llm_request_async("resume", messages=messages, response_format={"type": "json_object"})
        parsed = json.loads(response_content)
        if prefilter is not None:
            parsed["keyword_prefilter"] = prefilter
        return parsed
    except TokenExhaustionError:
        raise
    except Exception as e:
        raise Exception(f"CV/JD Matcher API Error: {str(e)}")
