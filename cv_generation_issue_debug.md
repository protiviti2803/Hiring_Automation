# Resume Standardization Tool: Debugging & Generation Analysis

This document details the debugging analysis of the **Resume Standardization Tool** in the Protiviti Hiring Automation Pipeline, explaining why the Protiviti-format PowerPoint resume generation fails and outlining the steps to fix it.

---

## 1. Executive Summary

- **The Issue:** The background worker (`cv_worker.py`) fails to process CV standardization jobs, leaving them in a `PENDING` or `FAILED` state. As a result, attempts to download the PowerPoint file fail with a `400 Bad Request` ("Job is not completed yet").
- **The Core Reason:** The default model (**`openai/gpt-oss-20b`**) lacks the reasoning capacity to simultaneously follow the complex, detailed instructions in the system prompt ([`CV_prompt.txt`](file:///C:/Works/Hiring_Automation_Pipeline/HR_Automation_Pipeline/app/assests/CV_prompt.txt)) and output a structured JSON schema. The resulting formatting conflicts cause the Hugging Face router to reject the output with a `400 Bad Request (json_validate_failed)`.
- **The Resolution:** Upgrading the active model to **`openai/gpt-oss-120b`** in the workspace configuration completely resolves the issue, producing valid Protiviti-format JSON profiles that populate PPTX files successfully.

---

## 2. Technical Root Cause Analysis

### A. Model Capacity vs. Prompt Complexity
The system prompt [`CV_prompt.txt`](file:///C:/Works/Hiring_Automation_Pipeline/HR_Automation_Pipeline/app/assests/CV_prompt.txt) is highly detailed (225 lines) and enforces multiple constraints:
- Specific rephrasing requirements (Task 1).
- Employer anonymization rules (General Rules).
- Bullet point scaling based on project counts (Task 3).
- Grammatical parallelism (Task 3).
- Strict constraints on sidebar listings (Task 4 - exactly 20 keywords, no padding).

While necessary for maintaining the Protiviti template style, these instructions present a high cognitive load. The default **20B parameter model** is too small to maintain all these formatting rules in context while outputting correct JSON structure.

### B. Format Contradictions
There is a layout contradiction between the system prompt and the API wrapper:
- The system prompt ([`CV_prompt.txt`](file:///C:/Works/Hiring_Automation_Pipeline/HR_Automation_Pipeline/app/assests/CV_prompt.txt)) tells the model to output plain text headers and lists:
  - *Task 3:* "Format: Industry Description – Project Theme, Role: XXXXX, Bullet..."
  - *Task 4:* "One keyword per line..."
- The API wrapper in [`cv_worker.py`](file:///c:/Works/Hiring_Automation_Pipeline/HR_Automation_Pipeline/app/services/cv_worker.py#L49-L61) appends instructions to return a structured JSON object:
  - `"IMPORTANT: You MUST respond strictly with a valid JSON object containing exactly 'professional_summary', 'industry_expertise', 'major_project_experience'..."`

When the smaller 20B model runs, it tries to output the text formatting specified in the text instructions (like markdown lists or headers) instead of pure JSON lists, causing the validation to fail.

### C. Grammar-Constrained Decoding Constraints (Hugging Face Router)
The Hugging Face router endpoint (`https://router.huggingface.co/v1`) enforces grammar constraints when `response_format={"type": "json_object"}` is used. If the model starts producing anything that violates the JSON grammar (such as markdown code fences like ````json` or conversational prefaces), the server terminates the generation and returns:
```json
{"error": {"message": "Failed to validate JSON. Please adjust your prompt.", "type": "invalid_request_error", "code": "json_validate_failed"}}
```

---

## 3. Evidence & Test Run Verification

During debug testing:

1. **`openai/gpt-oss-20b` (Default Configuration):**
   - Querying the model with JSON-mode constraint raises an immediate `BadRequestError (json_validate_failed)` because the output format deviates from standard JSON.
   - Querying without JSON-mode returns a completely blank response from the router.
2. **`openai/gpt-oss-120b` (Upgraded Configuration):**
   - Running the exact same prompt with the 120B model succeeds instantly, delivering a clean, valid JSON profile.
   - **Match Score Evaluation:** `95%`
   - **JSON Structure output:**
     ```json
     {
       "professional_summary": "Test Candidate has 5 years of experience as a Business Analyst...",
       "industry_expertise": ["Consulting", "Financial Services"],
       "major_project_experience": [{"project_title": "...", "role": "...", "bullets": [...]}],
       "areas_of_expertise": [...],
       "education": ["MBA in Finance"]
     }
     ```

---

## 4. How to Fix It

To resolve the issue across the entire application, define the model ID in the `.env` file. This tells all endpoints and background workers to use the 120B model:

### Step 1: Update the Environment Configuration
Open your [`.env`](file:///c:/Works/Hiring_Automation_Pipeline/HR_Automation_Pipeline/.env) file and append the following environment variable:

```env
GPT_OSS_20B_MODEL_ID=openai/gpt-oss-120b
```

### Step 2: Restart the Application / CV Worker
Since environment variables are loaded at startup, restart your FastAPI dev server or standalone CV worker process:
```powershell
python app/services/cv_worker.py
```

All pending jobs in the queue will be processed by the 120B model, turning their status to `COMPLETED` and allowing successful PPTX PowerPoint resume downloads.
