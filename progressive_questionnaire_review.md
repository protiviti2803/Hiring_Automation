# Progressive Questionnaire & Priority Queue System: Architecture Review

This document provides a detailed walkthrough of the **Progressive Questionnaire System** designed for the Protiviti HR AI Hiring Portal. It explains the priority queue algorithms, candidate-to-candidate queue transitions, database schemas, and master-level synchronization.

---

## 1. Dual-Queue Priority System (PQ1 & PQ2)

The core interview question engine uses two priority queues backed by a **HashMap Frequency Registry** to dynamically retrieve, sort, and evict questions based on ask frequencies.

```
                    ┌──────────────────────────────┐
                    │  HashMap Frequency Registry  │ (Holds global asked count)
                    └──────────────┬───────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
┌─────────────────┐                                 ┌─────────────────┐
│       PQ1       │                                 │       PQ2       │
│  Session Queue  │                                 │ Database Queue  │
│ (Max Size: 15)  │                                 │(Unlimited Size) │
└────────┬────────┘                                 └────────┬────────┘
         │                                                   │
         │ (Pull up to target_count)                         │ (Fill remaining balance)
         └─────────────────────────┬─────────────────────────┘
                                   ▼
                       ┌──────────────────────┐
                       │  Selected Prep Kit   │ (5 to 15 questions)
                       └──────────────────────┘
```

### A. Data Structure: Max-Priority Queue
Python's standard library `heapq` implements a binary min-heap. To achieve **Max-Priority** behavior (retrieving the highest-frequency questions first), we negate the priorities (frequencies) when storing them:
*   **Heap Entry:** `(-frequency, entry_counter, question_id)`
*   **Associated Data Map:** `_entry_finder = {question_id: [priority, counter, question_data]}`
*   **Deleted Mark:** If a question is updated or deleted, it is not removed immediately from the heap array (which is $O(N)$). Instead, its registry entry in `_entry_finder` is marked as a placeholder constant (`self.REMOVED`), and it is ignored during pop operations ($O(1)$ lazy deletion).

### B. PQ1 (Session Queue)
*   **Purpose:** Stores questions asked to previous candidates during the active session.
*   **Constraint:** Maximum size of 15 questions.
*   **Dynamic Eviction:** When a candidate's session logs are processed, any new question is enqueued. If PQ1's size exceeds 15, the queue executes `pop_min()` which searches the heap, finds the question with the **lowest overall frequency**, and evicts it to preserve the most relevant questions.

### C. PQ2 (Database Queue)
*   **Purpose:** Stores the baseline role questions loaded from the Excel database.
*   **Constraint:** Unlimited size, ordered by highest frequency first.
*   **Fallback:** If the session queue (`PQ1`) has fewer than the requested `target_count` of questions, the engine pulls the highest-priority questions from `PQ2` to make up the balance.

---

## 2. Passing Questions to the Next Candidate (Local Flow)

When an interviewer logs questions for Candidate #1 (Yash Chunekar), they pass them on to Candidate #2 (ABHISHEK SHARMA) via the following pipeline:

### Step A: Send questions via UI
Clicking the **"Send"** button triggers a POST request to `/api/session-questions/save`.
1. Splits input text by lines/semicolons to handle batch questions.
2. Writes them to the `session_questions` SQLite table, mapped to the active `session_id`, `candidate_id`, and categorizes them (`"Technical"` for General, `"Domain"` for Domain).

### Step B: Load questions for next Candidate
Clicking the **"Prep Kit"** button on the next candidate triggers a call to `/api/agent/progressive-prep`, which reads all logged session questions.
1. **Deduplication:** The backend loops through all questions and tracks seen question text in a dictionary (`seen_texts = {}`). If a question was logged multiple times, it **reuses the same ID** instead of generating a new UUID. This prevents duplicate objects from bloating the session queue.
2. **Frequency Registry Integration:** The list of previous questions is loaded into the progressive system using `post_interview_update(formatted_prev)`. Frequencies are incremented by `1`.
3. **Queue Selection:** The system compiles the final kit using `fetch_interview_questions(target_count)` which returns Candidate #1's questions first, followed by PQ2 fallbacks.

---

## 3. Saving Questions to the Master DB (UPSERT)

When the recruiter clicks the **"Save"** button, the system adds the questions to the global question bank.

*   **Endpoint:** `/api/master-questions/save`
*   **Method:** Executes `save_to_master_db(question_text, type)`.
*   **Logic:** Uses SQLite's native `ON CONFLICT` clause. If the question text is already in the table, it automatically increments the existing frequency instead of throwing an error or creating a duplicate row.

```sql
INSERT INTO master_questions (question_text, type, frequency)
VALUES (?, ?, 1)
ON CONFLICT (question_text) 
DO UPDATE SET frequency = master_questions.frequency + 1;
```

---

## 4. Database Table Design: Domain vs. General

To support automated partitioning, the `master_questions` table uses an enum check constraint, and the frontend matches categories case-insensitively.

### A. SQLite Table Schemas

```sql
-- Global Question Bank
CREATE TABLE master_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text TEXT UNIQUE,                      -- Enforces deduplication
    frequency INTEGER DEFAULT 1,                     -- Updates automatically via UPSERT
    type TEXT CHECK(type IN ('GENERIC', 'DOMAIN'))   -- Restricts category types
);

-- Active Session Logs
CREATE TABLE session_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    candidate_id INTEGER,
    raw_text TEXT,
    standardized_question TEXT,
    category TEXT                                    -- 'Technical' (General) or 'Domain'
);
```

### B. Categorization Logic (Case-Insensitive Substrings)
To remain fully immune to casing variations (e.g. `'Domain'` vs `'DOMAIN'`) and descriptive categories (e.g. `"Domain Knowledge"`, `"Transaction Banking Domain"`), the UI uses substring checks:

1.  **Domain Questions:** If the category string contains the word `'domain'` (case-insensitive), it is routed to the green-shaded **Domain Questions** column.
2.  **General Questions:** If it does not contain the word `'domain'` (e.g. it is `'Technical'`, `'Scenario'`, `'Behavioral'`, or `'Generic'`), it is routed to the yellow-shaded **General Questions** column.

```javascript
const genericQs = prepKitQuestions.filter(q => q && !(q.category || '').toLowerCase().includes('domain'));
const domainQs = prepKitQuestions.filter(q => q && (q.category || '').toLowerCase().includes('domain'));
```
