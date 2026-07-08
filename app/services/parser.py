import os

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text from a PDF file using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return "Error: pypdf library is not installed. Run 'pip install pypdf' to install it."
    
    if not os.path.exists(pdf_path):
        return f"Error: File not found at {pdf_path}"
    
    try:
        reader = PdfReader(pdf_path)
        text = []
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text)
    except Exception as e:
        return f"Error reading PDF file: {str(e)}"

def extract_text_from_docx(docx_path: str) -> str:
    """Extracts text from a DOCX file using python-docx."""
    try:
        import docx
    except ImportError:
        return "Error: python-docx library is not installed. Run 'pip install python-docx' to install it."
    
    if not os.path.exists(docx_path):
        return f"Error: File not found at {docx_path}"
    
    try:
        doc = docx.Document(docx_path)
        text = []
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text)
        return "\n".join(text)
    except Exception as e:
        return f"Error reading DOCX file: {str(e)}"

def extract_text_from_file(file_path: str) -> str:
    """Detects file type and extracts text."""
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    _, ext = os.path.splitext(file_path.lower())
    
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    elif ext in ['.txt', '.md']:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"Error reading text file: {str(e)}"
    else:
        return f"Error: Unsupported file format '{ext}'. Only PDF, DOCX, and TXT/MD files are supported."