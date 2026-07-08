import os
import sys
import asyncio
from dotenv import load_dotenv
from app.services.parser import extract_text_from_pdf
from app.services.matcher import compare_cv_with_jd_async

# Reconfigure stdout to use UTF-8 to prevent UnicodeEncodeError on Windows terminals
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def print_comparison_results(result: dict):
    # ANSI escape sequences for formatting
    HEADER = "\033[96m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    print("\n" + "=" * 60)
    print(f"{HEADER}{BOLD}CV VS JD SEMANTIC COMPARISON RESULTS{RESET}")
    print("=" * 60)
    
    score = result.get("overall_score", 0)
    score_color = GREEN if score >= 80 else (YELLOW if score >= 50 else RED)
    print(f"\n{BOLD}Overall Match Score:{RESET} {score_color}{BOLD}{score}/100{RESET}")
    
    print(f"\n{HEADER}{BOLD}Recommendation:{RESET}")
    rec = result.get("recommendation", {})
    status = rec.get("status", "N/A")
    status_color = GREEN if status.lower() in ["shortlist", "interview"] else (RED if status.lower() == "reject" else YELLOW)
    print(f"  {BOLD}Status:{RESET} {status_color}{BOLD}{status}{RESET}")
    print(f"  {BOLD}Reasoning:{RESET} {rec.get('reasoning', 'N/A')}")
    
    print(f"\n{HEADER}{BOLD}Skills Analysis:{RESET}")
    skills = result.get("skills_analysis", {})
    print(f"  {GREEN}Matching Skills:{RESET} {', '.join(skills.get('matching_skills', [])) or 'None'}")
    print(f"  {RED}Missing Critical Skills:{RESET} {', '.join(skills.get('missing_skills', [])) or 'None'}")
    print(f"  {YELLOW}Optional/Nice-to-Have Skills:{RESET} {', '.join(skills.get('optional_skills', [])) or 'None'}")
    
    print(f"\n{HEADER}{BOLD}Experience Alignment:{RESET}")
    print(f"  {result.get('experience_alignment', 'N/A')}")
    
    print(f"\n{HEADER}{BOLD}Candidate Strengths:{RESET}")
    for strength in result.get("strengths", []):
        print(f"  {GREEN}✔{RESET} {strength}")
    if not result.get("strengths"):
        print("  None identified.")
        
    print(f"\n{HEADER}{BOLD}Identified Gaps:{RESET}")
    for gap in result.get("gaps", []):
        print(f"  {RED}✘{RESET} {gap}")
    if not result.get("gaps"):
        print("  No significant gaps identified.")
        
    print("\n" + "=" * 60 + "\n")

async def main():
    if len(sys.argv) < 3:
        print("Usage: python cli_compare.py <path_to_resume_pdf> <path_to_jd_text_file>")
        sys.exit(1)
        
    resume_path = sys.argv[1]
    jd_path = sys.argv[2]
    
    # Load env variables from root folder
    root_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(dotenv_path=os.path.join(root_dir, ".env"))
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "GROQ_API_KEY" or api_key == "your_api_key_here":
        print("\033[91mError: GROQ_API_KEY is not set or is still the placeholder. Please set your key in the .env file.\033[0m")
        sys.exit(1)
        
    # Check if files exist
    if not os.path.exists(resume_path):
        print(f"\033[91mError: Resume file not found at '{resume_path}'.\033[0m")
        sys.exit(1)
        
    if not os.path.exists(jd_path):
        print(f"\033[91mError: JD file not found at '{jd_path}'.\033[0m")
        sys.exit(1)
        
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
        
    print(f"Reading JD: {jd_path} ...")
    try:
        with open(jd_path, "r", encoding="utf-8", errors="ignore") as f:
            jd_text = f.read()
        if not jd_text.strip():
            print("\033[91mError: JD text file is empty.\033[0m")
            sys.exit(1)
    except Exception as e:
        print(f"\033[91mError reading JD text file: {str(e)}\033[0m")
        sys.exit(1)
        
    print("Performing semantic comparison using Llama 3.3 70B on Groq ...")
    try:
        result = await compare_cv_with_jd_async(cv_text, jd_text, api_key)
        print_comparison_results(result)
    except Exception as e:
        print(f"\033[91mError during comparison: {str(e)}\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
