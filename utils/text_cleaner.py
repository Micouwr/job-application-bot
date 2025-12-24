import re

def clean_resume_text(text: str) -> str:
    """
    Applies a series of regular expression substitutions to clean up
    common text extraction issues from resumes, especially from PDFs.
    """
    # Comprehensive resume formatting fixes

    # Fix header formatting - separate name and contact info
    text = re.sub(r'(WILLIAM\s+RYAN\s+MICOU)\s+(Louisville,\s+KY\s+•)', r'\1\n\2', text)

    # Fix Professional Summary - join broken sentences
    text = re.sub(r'(including high-volume service desk operations within regulated enterprise environments)\s*\n\s*([.])', r'\1 \2', text)
    text = re.sub(r'(delivering sustained results)\s*\n\s*(\([^)]+\)\.)', r'\1 \2', text)
    text = re.sub(r'(high-volume service desk operations within regulated enterprise environments)\s*\n\s*([.])', r'\1 \2', text)

    # Join any other broken sentences in the summary
    text = re.sub(r'([^.!?\s])\s*\n\s*([A-Z][^\n]*)', r'\1 \2', text)

    # Fix AI Projects formatting - remove ○ symbols and format properly
    text = re.sub(r'○\s+', '', text)

    # Fix Education & Certifications formatting
    text = re.sub(r'●\s*Certifications\s*\n\s*:\s*([A-Z])', r'● Certifications - \1', text)
    text = re.sub(r'●\s*Education\s*\n\s*:\s*([A-Z])', r'● Education - \1', text)

    # Add proper spacing between sections
    text = re.sub(r'(PROFESSIONAL\s+SUMMARY)', r'\n\n\1', text)
    text = re.sub(r'(CORE\s+CAPABILITIES)', r'\n\n\1', text)
    text = re.sub(r'(AI\s+PROJECTS)', r'\n\n\1', text)
    text = re.sub(r'(PROFESSIONAL\s+EXPERIENCE)', r'\n\n\1', text)
    text = re.sub(r'(EDUCATION\s+&\s+CERTIFICATIONS)', r'\n\n\1', text)

    # Fix specific issues with AI Projects section
    text = re.sub(r'(●\s+AI\s+Triage\s+Bot[^\n]+)\s+Orchestrated', r'\1\n\nOrchestrated', text)
    text = re.sub(r'(Repository:[^\n]+)\s*(●\s+Job\s+Application\s+Bot)', r'\1\n\n\2', text)

    # More comprehensive fix for AI Projects section
    text = re.sub(r'(●\s+AI\s+Triage\s+Bot[^\n]+)\s+○\s+(Orchestrated[^.]+\.)\s*○\s+(Applied[^.]+\.)\s*○\s+(Speciﬁed[^.]+\.)\s*○\s+(Documented[^.]+\.)\s*○\s+(Repository[^\n]+)\s*(●\s+Job\s+Application\s+Bot[^\n]+)\s+○\s+(Designed[^.]+\.)\s*○\s+(Integrated[^.]+\.)\s*○\s+(Speciﬁed[^.]+\.)\s*○\s+(Repository[^\n]+)', r'\1\n\n\2\n\3\n\4\n\5\n\6\n\n\7\n\n\8\n\9\n\10\n\11', text)

    # Fix Core Capabilities formatting - separate each capability on its own line
    text = re.sub(r'(●\s*AI Governance:[^●]+)(●\s*IT Service Management:)', r'\1\n\n\2', text)
    text = re.sub(r'(●\s*IT Service Management:[^●]+)(●\s*Technical Skills:)', r'\1\n\n\2', text)

    # Additional fixes for common word splits
    text = re.sub(r'deploy\s+ment', 'deployment', text)
    text = re.sub(r'hand\s+led', 'Handled', text)
    text = re.sub(r'Saa\s+S', 'SaaS', text)
    text = re.sub(r'Compu\s+Com', 'CompuCom', text)
    text = re.sub(r'Accu\s+Code', 'AccuCode', text)
    text = re.sub(r'Code\s+Louisville', 'CodeLouisville', text)
    text = re.sub(r'Comp\s+TIA', 'CompTIA', text)
    text = re.sub(r'Stand\s+ardized', 'standardized', text)
    text = re.sub(r'Manage\s+da', 'Managed a', text)
    text = re.sub(r'Managed([a-z]+)team', r'Managed \1 team', text)
    text = re.sub(r'Manage([a-z]+)team', r'Manage \1 team', text)

    # More comprehensive fixes for Professional Summary
    text = re.sub(r'(Strategic IT Operations leader with 20\+ years of comprehensive experience)\s*\n\s*(managing complex infrastructure)', r'\1 \2', text)
    text = re.sub(r'(Now specializing in AI governance and service delivery transformation)\s*\n\s*(I am certified in ISO/IEC 42001:2023)', r'\1 \2', text)
    text = re.sub(r'(Proven ability to architect and deploy custom AI solutions)\s*\n\s*(\(e\.g\., ISO-aligned triage)', r'\1 \2', text)

    # Ensure proper line breaks after periods in specific contexts
    text = re.sub(r'([.])\s*\n\s*([A-Z])', r'\1 \2', text)

    # Ensure no empty lines have whitespace
    text = re.sub(r'^\s+$', '', text, flags=re.MULTILINE)

    # Additional comprehensive fixes for the specific formatting issues
    text = re.sub(r'(regulated enterprise environments)\s*\n\s*([.])', r'\1 \2', text)
    text = re.sub(r'(sustained results\s*)\n\s*(\([^)]+\)\.)', r'\1 \2', text)

    # More comprehensive fix for AI Projects formatting
    text = re.sub(r'(●\s+Job\s+Application\s+Bot[^\n]+)\s+○\s+(Designed)', r'\1\n\n○ \2', text)

    # Fix specific AI Projects content formatting
    text = re.sub(r'(Repository:[^\n]+)\s*●\s*', r'\1\n\n● ', text)

    # Ensure each project detail is on its own line
    text = re.sub(r'([.])\s*\n\s*(Orchestrated|Applied|Speciﬁed|Documented|Designed|Integrated)', r'\1\n\2', text)

    # More specific fixes for the current output
    text = re.sub(r'Orchestrated this proof-of-concept ticket classiﬁcation system using Google Gemini 2.5 Flash\s*\.\s*\n\s*○', r'Orchestrated this proof-of-concept ticket classiﬁcation system using Google Gemini 2.5 Flash.\n\n', text)
    text = re.sub(r'Google Gemini 2.5 Flash\s*\.\s*\n\s*○\s+Applied', r'Google Gemini 2.5 Flash.\n\nApplied', text)

    return text
