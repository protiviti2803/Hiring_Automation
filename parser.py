import sys
from app.services.parser import extract_text_from_file

# Reconfigure stdout to use UTF-8 to prevent UnicodeEncodeError on Windows terminals
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parser.py <path_to_resume_or_document>")
        sys.exit(1)
        
    target_path = sys.argv[1]
    print(f"--- Extracting text from: {target_path} ---")
    extracted_text = extract_text_from_file(target_path)
    print("\n--- Extracted Content ---")
    print(extracted_text)
    print("-------------------------")
