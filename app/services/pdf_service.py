import os

def create_resume_pdf(title: str, text: str, output_path: str):
    """
    Creates a clean, standardized PDF file from text content natively in Python.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    def pdf_escape(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content_stream = []
    content_stream.append("BT")
    content_stream.append("/F1 16 Tf")
    content_stream.append("0.1 0.1 0.2 rg") # Dark Header
    content_stream.append("50 740 Td")
    
    clean_title = pdf_escape(title.replace(".pdf", "").replace("_", " ").upper())
    content_stream.append(f"({clean_title}) Tj")
    content_stream.append("0 -20 Td")
    content_stream.append("/F1 9 Tf")
    content_stream.append("0.3 0.3 0.4 rg")
    content_stream.append("(OFFICIAL RESUME / CANDIDATE DOSSIER) Tj")
    content_stream.append("0 -20 Td")
    
    y = 700
    for line in lines[:55]:
        clean = pdf_escape(line)
        if line.isupper() or line.endswith(":") or any(k in line.upper() for k in ["SUMMARY", "EXPERIENCE", "COMPETENCIES", "EDUCATION", "SKILLS"]):
            content_stream.append("/F1 11 Tf")
            content_stream.append("0.1 0.25 0.5 rg") # Accent Color
            content_stream.append("0 -18 Td")
            content_stream.append(f"({clean}) Tj")
            content_stream.append("/F1 9 Tf")
            content_stream.append("0.2 0.2 0.2 rg")
            content_stream.append("0 -4 Td")
        else:
            content_stream.append("0 -13 Td")
            content_stream.append(f"({clean[:95]}) Tj")
        y -= 13

    content_stream.append("ET")
    
    stream_data = "\n".join(content_stream).encode("latin1", errors="replace")
    stream_len = len(stream_data)
    
    pdf_template = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {stream_len} >>
stream
{stream_data.decode("latin1")}
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000240 00000 n 
0000000310 + {stream_len} n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
500
%%EOF
"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(pdf_template.encode("latin1", errors="replace"))
    return output_path
