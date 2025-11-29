import os
import logging
from pathlib import Path
from typing import List

# File reading handlers
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

# PDF generation handler
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not installed. PDF generation disabled.")


logger = logging.getLogger(__name__)

# --- Text Extraction Utility (Already defined) ---

def extract_text_from_file(filepath: str) -> str:
    """
    Reads content from .txt, .md, .pdf, and .docx files.
    """
    path = Path(filepath)
    extension = path.suffix.lower()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    # 1. Handle Plain Text / Markdown
    if extension in ['.txt', '.md', '.rtf']: 
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
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
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            raise ValueError(f"Could not extract text from DOCX: {e}")

    else:
        raise ValueError(f"Unsupported file format: {extension}")

# --- PDF Generation Utility (NEW) ---

def generate_pdf_from_markdown(markdown_content: str, output_path: str, is_cover_letter: bool = False):
    """
    Generates a PDF file from Markdown/plain text content using ReportLab.
    
    Args:
        markdown_content (str): The content to be converted.
        output_path (str): The destination file path for the PDF.
        is_cover_letter (bool): If True, uses a slightly different style (like left-justified).
        
    Raises:
        ValueError: If reportlab is not installed.
    """
    if not REPORTLAB_AVAILABLE:
        raise ValueError("ReportLab library is required for PDF generation. Please install it.")

    # 1. Setup Document and Styles
    doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=72, rightMargin=72, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    # Define custom styles
    styles.add(ParagraphStyle(name='Heading1', fontSize=18, spaceAfter=12, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Heading2', fontSize=14, spaceBefore=10, spaceAfter=6, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Body', fontSize=10, leading=14))
    styles.add(ParagraphStyle(name='ListItem', fontSize=10, leftIndent=18, firstLineIndent=-18, spaceBefore=4, spaceAfter=4))
    
    # If it's a cover letter, use standard left-alignment for the main body
    if is_cover_letter:
        main_style = styles['Body']
    else:
        # Default resume style
        main_style = styles['Body']


    # 2. Process Content Line by Line
    lines = markdown_content.split('\n')
    
    # Simple state machine to handle paragraphs and lists
    current_list_items: List[ListItem] = []
    
    def finalize_list():
        nonlocal current_list_items
        if current_list_items:
            # Use 'ul' for standard bullet lists
            list_flowable = ListFlowable(
                current_list_items,
                bulletType='bullet',
                bulletColor='black',
                start='bulletchar',
                bulletChar='•',
                leftIndent=25
            )
            story.append(list_flowable)
            story.append(Spacer(1, 4))
            current_list_items = []

    for line in lines:
        line = line.strip()
        if not line:
            finalize_list()
            story.append(Spacer(1, 6))
            continue

        # Handle Markdown Headings (Simple detection based on resume structure)
        if line.startswith('### '):
            finalize_list()
            text = line[4:].strip()
            p = Paragraph(text, styles['Heading2'])
            story.append(p)
            story.append(Spacer(1, 2))
        
        elif line.startswith('# ') and not is_cover_letter:
            # Assume the top line is the Name/Title
            finalize_list()
            text = line[2:].strip()
            p = Paragraph(text, styles['Heading1'])
            story.append(p)
            story.append(Spacer(1, 4))
            
        # Handle List Items (Markdown bullet point: *)
        elif line.startswith('* ') or line.startswith('- '):
            text = line[2:].strip()
            # Convert text (which might contain **bold**) to HTML format for ReportLab
            html_text = text.replace('**', '<b>').replace('__', '<b>')
            current_list_items.append(ListItem(Paragraph(html_text, styles['ListItem']), leftIndent=18))

        # Handle Standard Paragraph Text (used for address block or cover letter body)
        else:
            finalize_list()
            # Convert text (which might contain **bold**) to HTML format for ReportLab
            html_text = line.replace('**', '<b>').replace('__', '<b>')
            p = Paragraph(html_text, main_style)
            story.append(p)

    finalize_list() # Catch any list left open at the end

    # 3. Build the PDF
    try:
        doc.build(story)
    except Exception as e:
        logger.error(f"ReportLab PDF build failed: {e}")
        raise RuntimeError(f"Failed to generate PDF file: {e}")