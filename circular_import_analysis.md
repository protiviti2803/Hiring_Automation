# Circular Import Error Analysis & Resolution

This document explains the circular import error encountered while running `cli_compare.py`, why it occurred, and details the changes made to resolve it.

---

## 1. Why the Error Occurred

The error message was:
```text
ImportError: cannot import name 'extract_text_from_pdf' from partially initialized module 'app.services.parser' (most likely due to a circular import) (C:\Works\HR_Demo\app\services\parser.py)
```

### The Root Cause
The file `app/services/parser.py` (which should only contain helper utilities like `extract_text_from_pdf`) was accidentally overwritten with the contents of the CLI runner script `cli_compare.py`.

Here is the sequence of events that occurred when running `python cli_compare.py`:

1. **Execution starts**: Python begins compiling and executing `cli_compare.py`.
2. **First import**: `cli_compare.py` runs line 5: `from app.services.parser import extract_text_from_pdf`.
3. **Module initialization**: Python locates `app/services/parser.py`, registers it in `sys.modules` as a "partially initialized" module, and starts executing it.
4. **Self-import inside parser**: Because `app/services/parser.py` had the runner script's code, it attempted to run its own line 5: `from app.services.parser import extract_text_from_pdf`.
5. **ImportError**: Python saw that the module `app.services.parser` was already in the middle of initializing. Since the name `extract_text_from_pdf` did not exist in the module's namespace yet (due to the file contents being overwritten with runner logic), Python raised an `ImportError` citing a circular import.

---

## 2. Code Comparison & Points of Failure

### Old (Broken) Code Structure

#### **Broken `app/services/parser.py`**
This file had duplicate runner logic and attempted to import from itself:
```python
# app/services/parser.py (Accidentally overwritten with cli_compare.py code)
1: import os
2: import sys
3: import asyncio
4: from dotenv import load_dotenv
5: from app.services.parser import extract_text_from_pdf  # <-- ERROR: CIRCULAR SELF-IMPORT LOOP
6: from app.services.matcher import compare_cv_with_jd_async
...
```

#### **Broken `cli_compare.py`**
This file only supported PDF parsing and lacked dynamic text support:
```python
# cli_compare.py (Original PDF-only script)
...
88:     print(f"Parsing resume: {resume_path} ...")
89:     try:
90:         cv_text = extract_text_from_pdf(resume_path)  # <-- Only supported PDFs
91:         if not cv_text.strip():
92:             print("Error: Failed to extract text...")
...
```

---

## 3. The Changes Made to Resolve the Issue

We separated the code back into their correct concerns:
1. **Core library functions** stay in `app/services/parser.py`.
2. **CLI execution logic** stays in `cli_compare.py`.

### Resolved Code Structure

#### **Fixed `app/services/parser.py`**
We restored the file back to its correct state, containing only the parsing functions:
```python
# app/services/parser.py
import os

def extract_text_from_pdf(pdf_path: str) -> str:
    # (pypdf reader logic)
    ...

def extract_text_from_docx(docx_path: str) -> str:
    # (python-docx reader logic)
    ...

def extract_text_from_file(file_path: str) -> str:
    # (extension router logic)
    ...
```

#### **Fixed `cli_compare.py`**
We integrated the dynamic file format checking block directly here, allowing it to correctly parse either `.txt` or `.pdf` CV documents:
```python
# cli_compare.py
...
    # Dynamic parsing based on file extension (.pdf vs .txt)
    try:
        if resume_path.lower().endswith('.txt'):
            print(f"Reading text CV directly: {resume_path} ...")
            with open(resume_path, "r", encoding="utf-8", errors="ignore") as f:
                cv_text = f.read()
        elif resume_path.lower().endswith('.pdf'):
            print(f"Parsing PDF CV: {resume_path} ...")
            cv_text = extract_text_from_pdf(resume_path)
        else:
            print("\033[91mError: Unsupported CV format. Please provide a .pdf or .txt file.\033[0m")
            sys.exit(1)

        if not cv_text.strip():
            print("\033[91mError: CV text content is empty.\033[0m")
            sys.exit(1)
    except Exception as e:
        print(f"\033[91mError reading resume: {str(e)}\033[0m")
        sys.exit(1)
...
```
