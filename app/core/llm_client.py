import os
import time
import httpx
import json
from datetime import datetime, timedelta
from openai import OpenAI, AsyncOpenAI, APIStatusError, APITimeoutError

class TokenExhaustionError(Exception):
    """Raised when both primary and fallback LLM services fail with token exhaustion or server errors."""
    def __init__(self, retry_after: str, message: str = "API tokens exhausted."):
        self.retry_after = retry_after
        self.message = message
        super().__init__(f"{message} Please try again after {retry_after}.")

def parse_retry_after(headers) -> int:
    """Parses retry duration in seconds from API response headers."""
    # Look for typical retry-after headers
    for h in ["retry-after", "Retry-After", "x-ratelimit-reset", "X-Ratelimit-Reset", "x-ratelimit-remaining"]:
        val = headers.get(h)
        if val:
            try:
                val_float = float(val)
                # If value looks like an epoch timestamp (value > current epoch time)
                if val_float > 1e9:
                    diff = int(val_float - time.time())
                    return max(1, diff)
                return max(1, int(val_float))
            except ValueError:
                pass
    return 15 * 60  # Default fallback of 15 minutes

def handle_fallback_failure(e: Exception):
    """Processes exception from fallback LLM, extracts Retry-After duration, and raises TokenExhaustionError."""
    retry_seconds = None
    if isinstance(e, APIStatusError):
        # We handle 400, 402, 429, 500
        if e.status_code in [400, 402, 429, 500]:
            if hasattr(e, "response") and e.response is not None:
                retry_seconds = parse_retry_after(e.response.headers)
    
    if retry_seconds is None:
        retry_seconds = 15 * 60  # Default to 15 minutes
        
    target_time = datetime.now() + timedelta(seconds=retry_seconds)
    formatted_time = target_time.strftime("%H:%M:%S")
    raise TokenExhaustionError(retry_after=formatted_time)

def execute_llm_request(task_type: str, messages: list, response_format: dict = None, max_tokens: int = None) -> str:
    """
    Executes an LLM request synchronously using a unified fallback pattern.
    - task_type: 'general' (General/Llama -> Nemotron) or 'resume' (gpt-oss-120b/20b -> Nemotron)
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    general_model = os.getenv("GENERAL_PRIMARY_MODEL", "meta-llama/llama-3.1-8b-instruct")
    
    openrouter_key = os.getenv("OPEN_ROUTER_API_KEY")
    fallback_model = os.getenv("NVIDIA_FALLBACK_MODEL", "nvidia/nemotron-3.5-lightning:free")
    
    gpt_oss_model = os.getenv("GPT_OSS_120B_MODEL_ID") or os.getenv("GPT_OSS_20B_MODEL_ID") or "openai/gpt-oss-120b"
    
    # Configure endpoints
    openrouter_base_url = "https://openrouter.ai/api/v1"
    gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    
    headers = {
        "HTTP-Referer": "https://github.com/google/antigravity",
        "X-Title": "HR Hiring Automation Pipeline",
    }
    
    # Select primary configuration
    if task_type == "general":
        primary_model = general_model
        if "llama" in primary_model.lower():
            primary_client = OpenAI(api_key=openrouter_key, base_url=openrouter_base_url, default_headers=headers)
            if "llama-3.1-8b-instant" in primary_model.lower():
                primary_model = "meta-llama/llama-3.1-8b-instruct"
        else:
            primary_client = OpenAI(api_key=gemini_key, base_url=gemini_base_url)
    else:  # 'resume'
        primary_model = gpt_oss_model
        primary_client = OpenAI(api_key=openrouter_key, base_url=openrouter_base_url, default_headers=headers)
        
    fallback_client = OpenAI(api_key=openrouter_key, base_url=openrouter_base_url, default_headers=headers)
    
    # Try primary request
    try:
        timeout_val = 75.0 if task_type == "resume" else 35.0
        kwargs = {
            "model": primary_model,
            "messages": messages,
            "timeout": timeout_val
        }
        if response_format:
            kwargs["response_format"] = response_format
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        completion = primary_client.chat.completions.create(**kwargs)
        content = completion.choices[0].message.content
        if content:
            return content.strip()
        else:
            raise ValueError("Primary model returned an empty response.")
            
    except Exception as primary_err:
        # Silently log/print and redirect to fallback model
        print(f"[LLM Client] Primary model ({primary_model}) failed: {primary_err}. Silently redirecting to fallback ({fallback_model})...")
        
        try:
            kwargs_fallback = {
                "model": fallback_model,
                "messages": messages,
                "timeout": 45.0
            }
            if response_format:
                kwargs_fallback["response_format"] = response_format
            if max_tokens:
                kwargs_fallback["max_tokens"] = max_tokens
                
            completion = fallback_client.chat.completions.create(**kwargs_fallback)
            content = completion.choices[0].message.content
            if content:
                return content.strip()
            else:
                raise ValueError("Fallback model returned an empty response.")
        except Exception as fallback_err:
            print(f"[LLM Client] Fallback model ({fallback_model}) also failed: {fallback_err}")
            handle_fallback_failure(fallback_err)

async def execute_llm_request_async(task_type: str, messages: list, response_format: dict = None, max_tokens: int = None) -> str:
    """
    Executes an LLM request asynchronously using a unified fallback pattern.
    - task_type: 'general' (General/Llama -> Nemotron) or 'resume' (gpt-oss-120b/20b -> Nemotron)
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    general_model = os.getenv("GENERAL_PRIMARY_MODEL", "meta-llama/llama-3.1-8b-instruct")
    
    openrouter_key = os.getenv("OPEN_ROUTER_API_KEY")
    fallback_model = os.getenv("NVIDIA_FALLBACK_MODEL", "nvidia/nemotron-3.5-lightning:free")
    
    gpt_oss_model = os.getenv("GPT_OSS_120B_MODEL_ID") or os.getenv("GPT_OSS_20B_MODEL_ID") or "openai/gpt-oss-120b"
    
    # Configure endpoints
    openrouter_base_url = "https://openrouter.ai/api/v1"
    gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    
    headers = {
        "HTTP-Referer": "https://github.com/google/antigravity",
        "X-Title": "HR Hiring Automation Pipeline",
    }
    
    # Select primary configuration
    if task_type == "general":
        primary_model = general_model
        if "llama" in primary_model.lower():
            primary_client = AsyncOpenAI(api_key=openrouter_key, base_url=openrouter_base_url, default_headers=headers)
            if "llama-3.1-8b-instant" in primary_model.lower():
                primary_model = "meta-llama/llama-3.1-8b-instruct"
        else:
            primary_client = AsyncOpenAI(api_key=gemini_key, base_url=gemini_base_url)
    else:  # 'resume'
        primary_model = gpt_oss_model
        primary_client = AsyncOpenAI(api_key=openrouter_key, base_url=openrouter_base_url, default_headers=headers)
        
    fallback_client = AsyncOpenAI(api_key=openrouter_key, base_url=openrouter_base_url, default_headers=headers)
    
    # Try primary request
    try:
        timeout_val = 75.0 if task_type == "resume" else 35.0
        kwargs = {
            "model": primary_model,
            "messages": messages,
            "timeout": timeout_val
        }
        if response_format:
            kwargs["response_format"] = response_format
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        completion = await primary_client.chat.completions.create(**kwargs)
        content = completion.choices[0].message.content
        if content:
            return content.strip()
        else:
            raise ValueError("Primary model returned an empty response.")
            
    except Exception as primary_err:
        # Silently log/print and redirect to fallback model
        print(f"[LLM Client] Async Primary model ({primary_model}) failed: {primary_err}. Silently redirecting to fallback ({fallback_model})...")
        
        try:
            kwargs_fallback = {
                "model": fallback_model,
                "messages": messages,
                "timeout": 45.0
            }
            if response_format:
                kwargs_fallback["response_format"] = response_format
            if max_tokens:
                kwargs_fallback["max_tokens"] = max_tokens
                
            completion = await fallback_client.chat.completions.create(**kwargs_fallback)
            content = completion.choices[0].message.content
            if content:
                return content.strip()
            else:
                raise ValueError("Fallback model returned an empty response.")
        except Exception as fallback_err:
            print(f"[LLM Client] Async Fallback model ({fallback_model}) also failed: {fallback_err}")
            handle_fallback_failure(fallback_err)
