# 02 — Inline PDF Resume Viewer Modal

**Date:** 2026-07-20  
**Status:** ✅ Complete

---

## Context

When the HR clicked "View Resume", the resume text was displayed as plain text inside a modal. The user requested that resumes be displayed as embedded PDFs directly within the modal, similar to a reference screenshot showing an inline document viewer.

## Changes Made

### Backend — PDF Serving Endpoint
- Created `app/services/pdf_service.py` — a helper service that generates candidate resume PDFs on the fly using `reportlab`.
- Added `/api/resumes/pdf/{filename}` endpoint in `app/main.py` that serves PDF files with `Content-Disposition: inline` header, allowing browsers to render them in an `<iframe>` instead of triggering a download.

### Frontend — Modal PDF Rendering
- Updated `handleViewResume` in `app/static/script.js` to support an `isPdf` boolean flag.
- When `isPdf = true` (triggered by "View Resume" button clicks), the modal renders an `<iframe>` pointing to the PDF endpoint.
- When `isPdf = false` (triggered by "Accept" / "Reject" button clicks), the modal renders the original HTML email template content.

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `app/services/pdf_service.py` | **Created** | PDF generation service using `reportlab` |
| `app/main.py` | Modified | Added `/api/resumes/pdf/{filename}` endpoint with inline headers |
| `app/static/script.js` | Modified | Added `isPdf` flag to `handleViewResume`; iframe rendering for PDFs |

## Key Technical Detail

Starlette's `FileResponse` defaults to `Content-Disposition: attachment` if `filename` is passed as a keyword argument. Overriding with `headers={"Content-Disposition": "inline"}` forces browser-native PDF rendering inside iframes.

## Verification

- "View Resume" button opens modal with embedded PDF viewer
- "Accept Candidate" and "Reject Candidate" buttons still show HTML email templates
- No download prompts triggered for inline PDF viewing
