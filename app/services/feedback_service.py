"""
Client Feedback Analysis Service.

Compares post-interview client feedback against the ORIGINAL demand to surface
"out-of-the-box" skills the client asked about during the interview but never
listed in the original demand. Those newly-discovered skills are categorized
into four keyword buckets so the NEXT interview cycle can screen candidates for
them.

Two-layer pipeline (token optimization):
  Layer 1 - Cosine similarity pre-filter (TF-IDF, sklearn):
      Split feedback into sentences; keep only the sentences that are
      semantically DIFFERENT from the original demand (low similarity).
      Sentences already covered by the demand are dropped before any LLM call.
  Layer 2 - Deep LLM semantic categorization (Groq):
      Only the low-similarity sentences are sent to the LLM, which extracts and
      categorizes new keywords into Hard Skills, Soft Skills, Domain Knowledge,
      and Behavioural Knowledge.
"""
import json
import os

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.llm_client import TokenExhaustionError, execute_llm_request


CATEGORY_KEYS = ("hard_skills", "soft_skills", "domain_knowledge", "behavioral_knowledge")


def _split_sentences(text: str) -> list:
    import re
    parts = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text.strip()) if s.strip()]
    return parts if parts else [text.strip()]


def analyze_client_feedback(original_demand: str, raw_feedback: str, similarity_threshold: float = 0.30) -> dict:
    """
    Runs the two-layer pipeline and returns:
      {
        "status": "SUCCESS",
        "layer1_stats": {"total_sentences", "new_sentences_count", "threshold_used"},
        "summary": {"has_new_skills": bool, "reasoning": str},
        "keywords": {"hard_skills": [], "soft_skills": [], "domain_knowledge": [], "behavioral_knowledge": []}
      }
    """
    if not raw_feedback or not raw_feedback.strip():
        return {
            "status": "FAILED",
            "error": "raw_feedback is required.",
        }

    original_demand = (original_demand or "").strip()

    # ----------------------------------------------------------------
    # LAYER 1: Cosine similarity pre-filter
    # ----------------------------------------------------------------
    sentences = _split_sentences(raw_feedback)

    if original_demand:
        corpus = [original_demand] + sentences
        try:
            vectorizer = TfidfVectorizer(stop_words='english', min_df=1)
            tfidf = vectorizer.fit_transform(corpus)
            sims = cosine_similarity(tfidf[0], tfidf[1:]).flatten()
        except Exception:
            sims = [0.0] * len(sentences)
        new_sentences = [s for s, sim in zip(sentences, sims) if sim < similarity_threshold]
    else:
        # No demand to compare against -> everything is "new"
        new_sentences = sentences

    empty_keywords = {k: [] for k in CATEGORY_KEYS}

    if not new_sentences:
        return {
            "status": "SUCCESS",
            "layer1_stats": {
                "total_sentences": len(sentences),
                "new_sentences_count": 0,
                "threshold_used": similarity_threshold,
            },
            "summary": {
                "has_new_skills": False,
                "reasoning": "All feedback content is already covered by the original demand. No out-of-the-box skills found.",
            },
            "keywords": empty_keywords,
        }

    # ----------------------------------------------------------------
    # LAYER 2: Deep LLM semantic categorization
    # ----------------------------------------------------------------
    filtered_text = " ".join(new_sentences)

    system_prompt = (
        "You are an expert HR requirements analyst. During interviews, clients often probe for skills "
        "they never wrote in the original job demand. Your job is to read post-interview feedback that has "
        "already been pre-filtered to be DIFFERENT from the original demand, then extract and categorize any "
        "genuinely NEW skills, concepts, or expectations into exactly four categories.\n\n"
        "CATEGORIES:\n"
        "- hard_skills: Technical tools, programming languages, databases, frameworks, platforms, or specific methodologies (e.g. SQL, Swift, JIRA, Agile).\n"
        "- soft_skills: Communication, leadership, adaptability, stakeholder management, and similar interpersonal traits.\n"
        "- domain_knowledge: Business/operational verticals or regulatory areas (e.g. FX settlement, payments processing, mortgage origination).\n"
        "- behavioral_knowledge: Situational scenarios, conflict resolution, working under pressure, culture-fit signals.\n\n"
        "RULES:\n"
        "1. Only extract skills genuinely NEW versus the original demand.\n"
        "2. Each item is a short keyword or noun phrase (2-6 words), NOT a sentence.\n"
        "3. Empty category -> return [].\n"
        "4. has_new_skills is true only if at least one category is non-empty.\n\n"
        "Respond STRICTLY as JSON:\n"
        "{\n"
        '  "summary": {"has_new_skills": true, "reasoning": "one-sentence explanation"},\n'
        '  "keywords": {"hard_skills": [], "soft_skills": [], "domain_knowledge": [], "behavioral_knowledge": []}\n'
        "}"
    )

    user_prompt = (
        f"ORIGINAL DEMAND (context only - do NOT re-extract what is already here):\n"
        f'"""\n{original_demand[:2500]}\n"""\n\n'
        f"NEW / OUT-OF-THE-BOX FEEDBACK (extract & categorize these):\n"
        f'"""\n{filtered_text}\n"""'
    )

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response_content = execute_llm_request("general", messages=messages, response_format={"type": "json_object"})
        result = json.loads(response_content)
    except TokenExhaustionError:
        raise
    except Exception as e:
        return {"status": "FAILED", "error": f"LLM categorization failed: {str(e)}"}

    summary = result.get("summary", {"has_new_skills": False, "reasoning": "LLM returned an unexpected structure."})
    keywords = result.get("keywords", {})
    for key in CATEGORY_KEYS:
        if key not in keywords or not isinstance(keywords[key], list):
            keywords[key] = []
    # keep only the four known keys
    keywords = {k: keywords[k] for k in CATEGORY_KEYS}

    return {
        "status": "SUCCESS",
        "layer1_stats": {
            "total_sentences": len(sentences),
            "new_sentences_count": len(new_sentences),
            "threshold_used": similarity_threshold,
        },
        "summary": summary,
        "keywords": keywords,
    }
