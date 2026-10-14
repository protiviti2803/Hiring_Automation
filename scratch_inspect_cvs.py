import os

for f in ["Extracted_CV.txt", "Extracted_CV2.txt", "Extracted_CV3.txt", "Extracted_CV4.txt"]:
    path = os.path.join("app/assests", f)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as fp:
            content = fp.read()
        print(f"=== {f} ({len(content)} chars, {len(content.split())} words, {len(content.splitlines())} lines) ===")
        print("First 300 chars:\n", content[:300])
        print("...\n")
