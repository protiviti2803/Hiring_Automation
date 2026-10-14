# Interview Sessions Pipeline: Debugging & Fixes Report

This document details the in-depth analysis of the issues identified in the interview session functionality of the Hiring Automation Portal, along with the implemented fixes.

---

## 1. Issue 1: Progressive Question Passing (Candidate #1 ➔ Candidate #2)

### Functionality Details
When Candidate 1's interview is completed, their questions (general and domain specific) are saved in the `session_questions` table. When the user assembles the prep kit for Candidate 2, the portal loads these questions to build the progressive interview questionnaire.

#### How They are Passed
1. **Frontend Call:** In [script.js](file:///c:/Works/Hiring_Automation_Pipeline/HR_Automation_Pipeline/app/static/script.js), clicking "Prep Kit" fetches all logged questions for the current session via `/api/sessions/{session_id}/questions` and forwards them to `/api/agent/progressive-prep`.
2. **Deduplication & Frequency Mapping:** Inside [cognitive_engine.py](file:///c:/Works/Hiring_Automation_Pipeline/HR_Automation_Pipeline/app/services/cognitive_engine.py), the backend deduplicates question texts using `seen_texts`. It matches each question with the baseline Excel questions in `PQ2` (Database Queue) to maintain correct global frequencies.
3. **Queue Insertion:** `post_interview_update()` increments each question's frequency by `1` and pushes them to `PQ1` (Session Queue).
4. **Question Fetching:** [fetch_interview_questions()](file:///c:/Works/Hiring_Automation_Pipeline/HR_Automation_Pipeline/app/services/progressive_interview_system.py) fetches up to `target_count` questions:
   - First, it pulls all questions from `PQ1` (which contains Candidate 1's questions, now with higher frequencies).
   - Second, if there is a remaining balance, it fills it with the highest frequency baseline questions from `PQ2`.

---

## 2. Issue 2: Consolidated Insights 500 Error & Master DB Save Failure

### Root Cause
Both the "Consolidated Insights" action (endpoint `/api/final-consolidation`) and the "Save to Master Database" action (endpoint `/api/master-questions/save`) failed with a **500 Internal Server Error** due to invalid SQLite syntax in the `ON CONFLICT` clauses:
- `DO UPDATE SET frequency = master_questions.frequency + 1;`
- SQLite does **not** allow qualifying column names with the table name (i.e. `master_questions.frequency`) in the `SET` assignment of the `ON CONFLICT DO UPDATE` clause. It throws `sqlite3.OperationalError: no such column: master_questions.frequency`.

### Fix Implemented
Simplified the `SET` expressions by removing the `master_questions.` prefix.
For `save_to_master_db` and `run_session_consolidation_agent`:
```sql
ON CONFLICT (question_text) 
DO UPDATE SET frequency = frequency + ?;
```

---

## 3. Issue 3: Stacking of Questions under General Category & Labeling

### Root Causes
When consolidating questions, they did not split into "General" and "Domain" stacks, and generic questions in the prep kit were labeled as "Technical".

#### A. Lack of Strict Output Format in Consolidation LLM Prompt & Frontend Mismatches
1. The LLM consolidator system prompt in `run_session_consolidation_agent` did not restrict the category output of `inserts` to `'GENERIC'` or `'DOMAIN'`.
2. The consolidator LLM grouped questions under dynamic categories, but the frontend code was filtering based on specific properties (`c.name || c.category`). Since these keys did not match the LLM output key (`category_name`), all categories failed the substring filter and defaulted to the General Questions column.
3. Actual question text check for updates in `/api/final-consolidation` default to `"GENERIC"` because question text itself rarely contains the word `"domain"`.

#### B. Default Question Category Labeling
General/behavioral questions (e.g., *"Introduce yourself"*) were labeled as `"Technical"` because the Excel baseline parser and manual question saving endpoint defaulted generic questions to the label `"Technical"`.

### Fixes Implemented
1. **Consolidator Agent Prompt Update:** The consolidation LLM is explicitly instructed to group questions into exactly two categories under `pdf_structure.categories`: `"General Questions"` and `"Domain Questions"`.
2. **Frontend Compatibility Mapping:** In `run_session_consolidation_agent`, the backend loops over LLM categories and ensures that `category_name`, `category`, and `name` are all populated. This ensures compatibility with the frontend filter.
3. **Lookup Stored Categories:** The API now builds a dictionary of existing master questions and checks their true stored category (from the DB) for updates to prevent them from falling back to `"GENERIC"`.
4. **General Category Normalization:** Updated the baseline Excel parser, progressive prep kit assembly, and manual question saving to default generic/behavioral questions to `"General"` (instead of `"Technical"`).
