import os
import logging
from pathlib import Path

# Import handlers for specific file types
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

logger = logging.getLogger(__name__)

def extract_text_from_file(filepath: str) -> str:
    """
    Reads content from .txt, .md, .pdf, and .docx files.
    
    Args:
        filepath (str): The path to the file.
        
    Returns:
        str: The extracted text content.
        
    Raises:
        ValueError: If the file type is unsupported or a library is missing.
    """
    path = Path(filepath)
    extension = path.suffix.lower()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    # 1. Handle Plain Text / Markdown
    if extension in ['.txt', '.md', '.rtf']: 
        # Note: Basic RTF reading as text; for complex RTF, a specific library is needed.
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback for older encodings
            with open(path, 'r', encoding='latin-1') as f:
                return f.read()

    # 2. Handle PDF
    elif extension == '.pdf':
        if not PyPDF2:
            raise ValueError("PyPDF2 library not installed. Cannot read PDF files.")
        
        text_content = []
        try:
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text_content.append(page.extract_text())
            return "\n".join(text_content)
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            raise ValueError(f"Could not extract text from PDF: {e}")

    # 3. Handle Word Documents (.docx)
    elif extension == '.docx':
        if not docx:
            raise ValueError("python-docx library not installed. Cannot read DOCX files.")
        
        try:
            doc = docx.Document(path)
            # Extract text from paragraphs
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            raise ValueError(f"Could not extract text from DOCX: {e}")

    else:
        raise ValueError(f"Unsupported file format: {extension}")