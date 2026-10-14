# 05 — Dynamic Interview Session Cards per JD Title

**Date:** 2026-07-22  
**Status:** ✅ Complete

---

## Context

When a new demand was submitted (e.g., "Expertise in using AI technologies in regular Transformation PM and BA work"), the system generated a JD with the title "Artificial Intelligence Business Analyst with Transformation PM Expertise". However, when resumes were uploaded and candidates accepted, they were **all stacked under the generic "Business Analyst (BA)"** session card instead of getting their own dedicated card.

The user's requirement: **every unique JD title must create its own dedicated session card** under Interview Sessions, and candidates for that demand must be stacked under their specific card.

## Changes Made

### 1. Persistent `activeJobTitle` State
- Added `activeJobTitle` state hook in `App` component to preserve the exact generated JD title.
- Unlike `navbarTitle` (which changes during upload/processing to "Analyzing Resumes…", "Evaluations Complete", etc.), `activeJobTitle` holds the original JD title steady.

### 2. Prop Drilling: `jdTitle`
- Passed `activeJobTitle` as `jdTitle` prop through the component chain:
  - `App` → `ChatBubble` → `GeneratedContentCard`
- `GeneratedContentCard` uses `jdTitle` as the **primary** role identifier for the candidate accept payload.

### 3. Candidate Accept Payload Update
- Updated the `/api/candidates/accept` fetch body to use `jdTitle` (the exact generated heading) as the `role` field, instead of falling back to the parsed `jobTitle` from the evaluation summary text.
- Fallback chain: `jdTitle` → `parsed.jobTitle` → `'Business Analyst (BA)'`

### 4. State Synchronization
- `activeJobTitle` is set in:
  - `handleSend` — when a new JD is generated
  - `onSelectHistoryItem` — when a historical JD is loaded
  - `useEffect([activeSession])` — when switching between sessions
- `activeJobTitle` is cleared when switching to `'new'` or `'session-saved'` views.

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `app/static/script.js` | Modified | Added `activeJobTitle` state; updated prop chain; updated accept payload |

## Architecture

```
App (activeJobTitle state)
 ├── ChatBubble (jdTitle prop)
 │    └── GeneratedContentCard (jdTitle prop)
 │         └── Accept Candidate → role: jdTitle
 └── handleSend → setActiveJobTitle(jobTitle)
```

## Verification

- Generating a JD titled "Artificial Intelligence Business Analyst with Transformation PM Expertise" and accepting a candidate creates a dedicated session card with that exact title ✅
- Candidates for different demands are no longer all stacked under "Business Analyst (BA)" ✅
- Existing session cards (BA, PM, Backend Engineer, etc.) remain unaffected ✅
