import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
import os
import sys
import threading
import queue
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import OUTPUT_PATH, DB_PATH, MIN_MATCH_THRESHOLD
from database import DatabaseManager
from tailor import process_and_tailor_from_gui
from models.resume_model import ResumeModel
from AI.match_analyzer import analyze_match

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class JobAppTkinter:
    def __init__(self, master=None):
        print("MAIN FILE EXECUTED - UNIQUE IDENTIFIER")
        self.master = master
        self.master.title("Job Application Bot - AI Resume Tailorer")
        self.master.geometry("1000x700")
        
        # Initialize models and database
        self.db_manager = DatabaseManager()
        self.resume_model = ResumeModel()
        self.selected_resume_path = None
        self.active_resume_id = None
        
        # Ensure output directory exists
        os.makedirs(OUTPUT_PATH, exist_ok=True)
        
        # Create default resume if none exists
        self._ensure_default_resume()
        
        # Queue for thread communication
        self.tailoring_queue = queue.Queue()
        
        # Initialize match analysis variables
        self.match_data = None
        
        # Initialize tooltip window
        self._tooltip_window = None
        
        # Initialize UI
        self._init_ui()
        
        # Check for API key
        self._check_api_key()
        
        # Start queue checker
        self._check_queue()
    
    def _ensure_default_resume(self):
        """Create default resume if no resumes exist in database"""
        resumes = self.resume_model.list_resumes()
        
        if not resumes:
            default_resume_text = """MICHELLE NICOLE
AI Developer & Automation Specialist
San Francisco Bay Area | michellenicole@example.com | (555) 123-4567 | linkedin.com/in/michellenicole | github.com/michellenicole

PROFESSIONAL SUMMARY
Innovative AI Developer with expertise in building intelligent automation systems and cross-platform desktop applications. Proven track record of implementing machine learning solutions that improve efficiency by up to 85%. Strong background in Python, GPT API integration, and PyInstaller deployment for macOS, Windows, and Linux.

TECHNICAL SKILLS
Languages: Python, JavaScript, SQL, Bash, HTML/CSS
AI/ML: GPT-4 API, LangChain, TensorFlow, Scikit-learn, Prompt Engineering
Tools: PyInstaller, Git, Docker, PostgreSQL, SQLite, REST APIs
Frameworks: Tkinter, PyQt, Flask, FastAPI, Node.js
Certifications: Two AI certifications (redacted for privacy)

PROFESSIONAL EXPERIENCE

Senior AI Developer | Tech Innovations Inc. | 2022-Present
- Developed AI-powered resume tailoring system using GPT-4 API, reducing application time by 80%
- Implemented cross-platform desktop application with PyInstaller for 500+ users
- Created automated job application bot that increased interview rate by 3x
- Led team of 3 developers in building machine learning pipeline

Full Stack Developer | Automation Solutions Corp. | 2020-2022
- Built web scraping automation tools that processed 10,000+ job postings daily
- Integrated multiple APIs (LinkedIn, Indeed) for seamless data collection
- Developed database systems for candidate tracking and analytics
- Deployed applications across Windows, macOS, and Linux platforms

AI Developer | Machine Learning Startup | 2019-2020
- Created predictive models for applicant tracking systems (ATS)
- Implemented natural language processing for resume optimization
- Built custom algorithms for job matching and candidate ranking

EDUCATION
Bachelor of Science in Computer Science
University of California, Berkeley | 2019
Relevant Coursework: Machine Learning, AI Systems, Data Structures, Algorithms

PROJECTS
Job Application Bot - AI Resume Tailorer
- Desktop application using Tkinter and GPT-4 API for automated resume tailoring
- Features: PDF upload, database management, cross-platform compatibility
- Technologies: Python, PyInstaller, SQLite, Threading

Cross-Platform Automation Suite
- Built with PyInstaller for deployment on Windows, macOS, and Linux
- Automated job search, application tracking, and follow-up emails
- Integrated with 15+ job boards via API and web scraping

AI Resume Analyzer & Optimizer
- Machine learning model analyzing resume effectiveness
- Provides suggestions for ATS optimization and keyword targeting
- Used by 200+ job seekers with 90% satisfaction rate

PROFESSIONAL DEVELOPMENT
- Continuous learning in AI/ML technologies and frameworks
- Active contributor to open-source automation projects
- Member: AI Developers Association, Python Software Foundation

REFERENCES
Available upon request. Technical portfolio and code samples accessible via GitHub repository.
"""
            
            # Save to file
            default_path = OUTPUT_PATH / "default_resume.txt"
            with open(default_path, 'w', encoding='utf-8') as f:
                f.write(default_resume_text)
            
            # Add to database
            self.resume_model.add_resume(str(default_path), "Default Resume", is_active=True)
            logging.info("Default resume created successfully")
    
    def _init_ui(self):
        """Initialize the main UI components"""
        # Main container
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create tabs in desired order
        self._create_add_job_tab()  # Job Management
        self._create_resume_mgmt_tab()
        self._create_tailored_docs_tab()
        self._create_output_tab()
        self._create_custom_prompt_tab()
        
        # Make notebook expandable
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
    
    def _create_add_job_tab(self):
        """Create the Add Job Application tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Job Management")
        
        # Job Details Section
        ttk.Label(tab, text="Job Title:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.job_title_entry = ttk.Entry(tab, width=50)
        self.job_title_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(tab, text="Company:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.company_entry = ttk.Entry(tab, width=50)
        self.company_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Role Level Selection
        ttk.Label(tab, text="Role Level:", font=('Arial', 10, 'bold')).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.role_var = tk.StringVar(value="Standard")
        role_combo = ttk.Combobox(tab, textvariable=self.role_var, values=["Standard", "Senior", "Lead", "Principal"], state='readonly')
        role_combo.grid(row=5, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Add tooltip with role definitions
        role_tooltip = "Role Definitions:\n"
        role_tooltip += "Standard: Entry to mid-level (0-5 years) - Core skills & direct contributions\n"
        role_tooltip += "Senior: Senior-level (5-10 years) - Leadership, strategic thinking, mentoring\n"
        role_tooltip += "Lead: Lead positions (8-15 years) - Team management, project leadership\n"
        role_tooltip += "Principal: Principal/architect (12+ years) - Technical architecture, innovation"
        role_combo.tooltip = role_tooltip
        
        # Bind hover event to show tooltip
        def show_role_tooltip(event):
            self.master.after(100, lambda: self._show_tooltip(event, role_tooltip))
        
        role_combo.bind('<Enter>', show_role_tooltip)
        role_combo.bind('<Leave>', lambda e: self._hide_tooltip())
        
        # Role Level Help Text
        role_help = ttk.Label(tab, text="Select role level that matches the job posting (see README for guidance)", 
                             font=('Arial', 9), foreground='blue')
        role_help.grid(row=7, column=1, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(tab, text="Job Description:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.job_desc_text = scrolledtext.ScrolledText(tab, width=80, height=15, wrap=tk.WORD)
        self.job_desc_text.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        ttk.Label(tab, text="Job URL:", font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.job_url_entry = ttk.Entry(tab, width=50)
        self.job_url_entry.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Status label for match analysis feedback
        self.status_label = ttk.Label(tab, text="Ready", font=('Arial', 9), foreground='red')
        self.status_label.grid(row=8, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        # Match score display
        self.match_label = ttk.Label(tab, text="Match Score: Not analyzed", font=('Arial', 10, 'bold'), foreground='blue')
        self.match_label.grid(row=9, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        # Buttons - Reordered as requested
        button_frame = ttk.Frame(tab)
        button_frame.grid(row=10, column=0, columnspan=4, pady=10)
        
        # Add Analyze Match button (first)
        self.analyze_button = ttk.Button(button_frame, text="Analyze Match", command=self.analyze_match)
        self.analyze_button.grid(row=0, column=0, padx=5)
        
        # Start Tailoring button (second)
        self.start_button = ttk.Button(button_frame, text="Start Tailoring", command=self.start_tailoring)
        self.start_button.grid(row=0, column=1, padx=5)
        
        # Clear Fields button (third)
        self.clear_button = ttk.Button(button_frame, text="Clear Fields", command=self.clear_fields)
        self.clear_button.grid(row=0, column=2, padx=5)
        
        # Quit button (fourth)
        self.quit_button = ttk.Button(button_frame, text="Quit", command=self.master.quit)
        self.quit_button.grid(row=0, column=3, padx=5)
        
        # DEBUG: Print to console to verify elements are created
        print("DEBUG: UI elements created - Status label, Match label, Analyze button")

        # Configure grid weights
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(2, weight=1)
    
    def _create_resume_mgmt_tab(self):
        """Create the Resume Management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Resume Management")
        
        # Resume List Section
        ttk.Label(tab, text="Available Resumes:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Create treeview for resumes
        columns = ('Name', 'Path', 'Active')
        self.resume_tree = ttk.Treeview(tab, columns=columns, show='headings', height=10)
        self.resume_tree.heading('Name', text='Resume Name')
        self.resume_tree.heading('Path', text='File Path')
        self.resume_tree.heading('Active', text='Active')
        
        self.resume_tree.column('Name', width=150)
        self.resume_tree.column('Path', width=400)
        self.resume_tree.column('Active', width=50)
        
        self.resume_tree.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.resume_tree.yview)
        self.resume_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=3, sticky=(tk.N, tk.S))
        
        # Bind selection event
        self.resume_tree.bind('<<TreeviewSelect>>', self._on_resume_select)
        
        # Resume Preview Section
        ttk.Label(tab, text="Resume Preview:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.resume_preview = scrolledtext.ScrolledText(tab, width=80, height=10, wrap=tk.WORD)
        self.resume_preview.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Buttons
        button_frame = ttk.Frame(tab)
        button_frame.grid(row=4, column=0, columnspan=4, pady=10)
        
        self.upload_button = ttk.Button(button_frame, text="Upload Resume", command=self.upload_resume)
        self.upload_button.grid(row=0, column=0, padx=5)
        
        self.delete_button = ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected_resume)
        self.delete_button.grid(row=0, column=1, padx=5)
        
        self.set_active_button = ttk.Button(button_frame, text="Set as Active", command=self.set_active_resume)
        self.set_active_button.grid(row=0, column=2, padx=5)
        
        # Refresh resume list
        self._refresh_resume_list()
        
        # Configure grid weights
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        tab.rowconfigure(3, weight=1)
    
    def _create_output_tab(self):
        """Create the Output/Logs tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Output & Logs")
        
        ttk.Label(tab, text="Application Logs:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(tab, width=80, height=25, wrap=tk.WORD)
        self.log_text.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Configure grid weights
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
    
    def _on_resume_select(self, event):
        """Handle resume selection in treeview"""
        selection = self.resume_tree.selection()
        if selection:
            item = self.resume_tree.item(selection[0])
            resume_path = item['values'][1]
            
            try:
                with open(resume_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.resume_preview.delete('1.0', tk.END)
                    self.resume_preview.insert('1.0', content)
            except Exception as e:
                self._log_message(f"Error loading resume preview: {e}", "error")
    
    def upload_resume(self):
        """Upload a new resume file"""
        file_path = filedialog.askopenfilename(
            title="Select Resume File",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("Text files", "*.txt"),
                ("Word files", "*.docx"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            # Get file name
            name = Path(file_path).stem
            
            # Handle PDF files
            if file_path.lower().endswith('.pdf'):
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        text_content = ""
                        for page in pdf_reader.pages:
                            text_content += page.extract_text() + "\n"
                    
                    # Save as text file
                    txt_path = OUTPUT_PATH / f"{name}.txt"
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    
                    file_path = str(txt_path)
                    
                    # ADDED: Warn about formatting loss
                    self._log_message(
                        f"PDF processed: {name} - extracted {len(text_content)} chars. "
                        f"Note: Formatting will be simplified in preview",
                        "info"
                    )
                except Exception as e:
                    self._log_message(f"PDF processing error: {e}", "error")
                    return
            
            # Add to database
            self.resume_model.add_resume(file_path, name, is_active=False)
            self._refresh_resume_list()
            self._log_message(f"Resume uploaded successfully: {name}", "info")
            
        except Exception as e:
            self._log_message(f"Error uploading resume: {e}", "error")
    
    def delete_selected_resume(self):
        """Delete the selected resume"""
        selection = self.resume_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a resume to delete")
            return
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this resume?"):
            return
        
        try:
            item = self.resume_tree.item(selection[0])
            resume_path = item['values'][1]
            
            # Delete from database
            self.resume_model.delete_resume_by_path(resume_path)
            
            # Refresh list
            self._refresh_resume_list()
            self.resume_preview.delete('1.0', tk.END)
            
            self._log_message("Resume deleted successfully", "info")
            
        except Exception as e:
            self._log_message(f"Error deleting resume: {e}", "error")
    
    def set_active_resume(self):
        """Set the selected resume as active"""
        selection = self.resume_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a resume to set as active")
            return
        
        try:
            item = self.resume_tree.item(selection[0])
            resume_path = item['values'][1]
            
            # Set as active in database
            self.resume_model.set_active_resume_by_path(resume_path)
            
            # Refresh list
            self._refresh_resume_list()
            
            self._log_message(f"Active resume set to: {item['values'][0]}", "info")
            
        except Exception as e:
            self._log_message(f"Error setting active resume: {e}", "error")
    
    def _load_selected_resume(self):
        """Load the currently active resume"""
        try:
            active_resume = self.resume_model.get_active_resume()
            if not active_resume:
                self._log_message("No active resume found. Please upload a resume first.", "error")
                return None
            
            resume_path = active_resume['file_path']
            
            with open(resume_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            self._log_message(f"Error loading resume: {e}", "error")
            return None
    
    def _refresh_resume_list(self):
        """Refresh the resume list in treeview"""
        # Clear existing items
        for item in self.resume_tree.get_children():
            self.resume_tree.delete(item)
        
        # Load resumes from database
        resumes = self.resume_model.list_resumes()
        for resume in resumes:
            active_status = "Yes" if resume['is_active'] else "No"
            self.resume_tree.insert('', tk.END, values=(
                resume['name'],
                resume['file_path'],
                active_status
            ))
        
        # Set active resume path
        active_resume = self.resume_model.get_active_resume()
        if active_resume:
            self.active_resume_id = active_resume['id']
    
    def analyze_match(self):
        """Analyze resume-job compatibility and display match score"""
        self._log_message("Starting match analysis...", "info")
        
        # Get active resume
        resume_text = self._load_selected_resume()
        if not resume_text:
            messagebox.showerror("Error", "No active resume loaded. Please upload and set a resume as Active first.")
            self._log_message("Match analysis failed: No active resume", "error")
            return
        
        # Get job description (ONLY requirement for match analysis - Golden Rule #1)
        job_description = self.job_desc_text.get('1.0', tk.END).strip()
        if not job_description or len(job_description) < 100:
            messagebox.showerror("Error", "Please enter a detailed job description (minimum 100 characters).")
            self._log_message("Match analysis failed: Job description too short", "error")
            return
        
        # Golden Rule #1: Job title and company are NOT required for compatibility checking
        
        try:
            # Call AI match analyzer
            self.status_label.config(text="Analyzing match...")
            self.master.update_idletasks()
            
            self.match_data = analyze_match(resume_text, job_description)
            score = self.match_data.get('overall_score', 0)
            
            # Update match display
            self.match_label.config(text=f"Match Score: {score}%")
            
            # Color coding based on score
            if score >= MIN_MATCH_THRESHOLD:
                self.match_label.config(foreground="green")
                self.start_button.config(state='normal')
                message = f"Strong match ({score}%)! Enter job title/company and click 'Start Tailoring' to proceed."
                self._log_message(f"Match analysis complete: {score}% (threshold met)", "info")
            else:
                self.match_label.config(foreground="red")
                self.start_button.config(state='disabled')
                message = f"Match score {score}% is below threshold ({MIN_MATCH_THRESHOLD}%). Improve resume or consider different role."
                self._log_message(f"Match analysis complete: {score}% (below threshold)", "warning")
            
            # Show detailed breakdown
            self._show_match_details()
            
            # Show summary message
            messagebox.showinfo("Match Analysis", message)
            
            self.status_label.config(text="Ready")
            
        except Exception as e:
            self._log_message(f"Match analysis error: {e}", "error")
            messagebox.showerror("Error", f"Match analysis failed: {e}")
            self.status_label.config(text="Ready")
            self.match_label.config(text="Error during analysis", foreground="red")

    def _show_match_details(self):
        """Display detailed match breakdown in a popup window"""
        if not self.match_data:
            return
        
        details_window = tk.Toplevel(self.master)
        details_window.title("Match Analysis Details")
        details_window.geometry("700x500")
        
        # Create scrollable text area
        details_text = scrolledtext.ScrolledText(details_window, width=80, height=25, wrap=tk.WORD)
        details_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Build details content
        score = self.match_data.get('overall_score', 0)
        
        # Handle complex data structures from AI response
        skills_data = self.match_data.get('skills_match', {})
        exp_data = self.match_data.get('experience_match', {})
        keywords_data = self.match_data.get('keywords_match', {})
        
        # Extract scores and analysis
        skills_score = skills_data.get('score', 'N/A') if isinstance(skills_data, dict) else skills_data
        exp_score = exp_data.get('score', 'N/A') if isinstance(exp_data, dict) else exp_data
        keywords_score = keywords_data.get('score', 'N/A') if isinstance(keywords_data, dict) else keywords_data
        
        # Extract analysis text
        skills_analysis = skills_data.get('analysis', []) if isinstance(skills_data, dict) else []
        exp_analysis = exp_data.get('analysis', []) if isinstance(exp_data, dict) else []
        keywords_analysis = keywords_data.get('analysis', []) if isinstance(keywords_data, dict) else []
        
        # Format analysis as readable text
        skills_text = '\n'.join([f'• {item}' if isinstance(item, str) else str(item) for item in skills_analysis]) if skills_analysis else 'No detailed analysis provided.'
        exp_text = '\n'.join([f'• {item}' if isinstance(item, str) else str(item) for item in exp_analysis]) if exp_analysis else 'No detailed analysis provided.'
        keywords_text = '\n'.join([f'• {item}' if isinstance(item, str) else str(item) for item in keywords_analysis]) if keywords_analysis else 'No detailed analysis provided.'
        
        # Get lists
        strengths = self.match_data.get('strengths', ['No strengths identified'])
        gaps = self.match_data.get('gaps', ['No gaps identified'])
        recommendations = self.match_data.get('recommendations', ['No recommendations'])
        
        # Format lists
        strengths_text = '\n'.join([f'• {item}' if isinstance(item, str) else str(item) for item in strengths])
        gaps_text = '\n'.join([f'• {item}' if isinstance(item, str) else str(item) for item in gaps])
        recommendations_text = '\n'.join([f'• {item}' if isinstance(item, str) else str(item) for item in recommendations])
        
        details = f"""MATCH SUMMARY
=============
Overall Score: {score}%
Skills Match: {skills_score}%
Experience Match: {exp_score}%
Keywords Match: {keywords_score}%

SKILLS ANALYSIS:
===============
{skills_text}

EXPERIENCE ANALYSIS:
==================
{exp_text}

KEYWORDS ANALYSIS:
=================
{keywords_text}

STRENGTHS:
==========
{strengths_text}

GAPS:
=====
{gaps_text}

RECOMMENDATIONS:
================
{recommendations_text}
"""
        
        details_text.insert('1.0', details)
        details_text.config(state='disabled')
        
        # Add close button
        close_button = ttk.Button(details_window, text="Close", command=details_window.destroy)
        close_button.pack(pady=5)
    
    def start_tailoring(self):
        """Validate all prerequisites and start AI-powered tailoring"""
        self._log_message("Validating tailoring prerequisites...", "info")
        
        # Prerequisites: job title, company, description, match score >= threshold
        job_title = self.job_title_entry.get().strip()
        if not job_title:
            messagebox.showerror("Missing Job Title", "Please enter a job title for file naming.")
            return
        
        company = self.company_entry.get().strip()
        if not company:
            messagebox.showerror("Missing Company", "Please enter a company name for file naming.")
            return
        
        job_description = self.job_desc_text.get('1.0', tk.END).strip()
        if not job_description or len(job_description) < 100:
            messagebox.showerror("Insufficient Job Description", "Please enter a detailed job description (minimum 100 characters).")
            return
        
        # Load resume
        resume_text = self._load_selected_resume()
        if not resume_text:
            messagebox.showerror("Missing Active Resume", "No active resume found. Please upload and set a resume as Active.")
            return
        
        # Check match data exists and meets threshold
        if not hasattr(self, 'match_data') or not self.match_data:
            messagebox.showerror("No Match Analysis", "Please click 'Analyze Match' first to check compatibility.")
            return
        
        score = self.match_data.get('overall_score', 0)
        if score < MIN_MATCH_THRESHOLD:
            messagebox.showerror("Match Too Low", f"Match score {score}% is below minimum threshold of {MIN_MATCH_THRESHOLD}%. Consider improving your resume or applying to a different role.")
            self._log_message(f"Tailoring blocked: match {score}% < threshold {MIN_MATCH_THRESHOLD}%", "warning")
            return
        
        # All validations passed - proceed with AI tailoring
        self.set_ui_enabled(False)
        self.status_label.config(text="Processing... Please wait", foreground="orange")
        self._log_message("Starting AI-powered tailoring...", "info")
        
        # Get role level
        role_level = self.role_var.get()
        
        # Start tailoring thread with AI engine
        thread = threading.Thread(
            target=self.tailor_application_thread,
            args=(job_title, company, job_description, self.job_url_entry.get(), resume_text, role_level, None)
        )
        thread.daemon = True
        thread.start()
    
    def tailor_application_thread(self, job_title, company, job_description, job_url, resume_text, role_level, custom_prompt):
        """Thread function for tailoring process"""
        try:
            # Process and tailor
            result = process_and_tailor_from_gui(
                resume_text, job_description, OUTPUT_PATH, 
                role_level, custom_prompt
            )
            
            # Check for required fields
            if not result or not result.get("resume_text") or not result.get("cover_letter"):
                raise Exception("AI returned incomplete or empty tailoring results")
            
            # FIXED: Use "info" instead of "success" for logging
            self._log_message("Resume tailoring completed successfully", "info")
            
            # Add to queue for main thread
            self.tailoring_queue.put({
                'status': 'success',
                'result': result,
                'job_title': job_title,
                'company': company
            })
            
        except Exception as e:
            self._log_message(f"Error during tailoring: {e}", "error")
            self.tailoring_queue.put({
                'status': 'error',
                'error': str(e)
            })
    
    def on_tailoring_complete(self, result_data):
        """Handle completion of tailoring process"""
        if result_data['status'] == 'error':
            self.status_label.config(text="Tailoring failed", foreground="red")
            messagebox.showerror("Error", f"Tailoring failed: {result_data['error']}")
            self.set_ui_enabled(True)
            return
        
        try:
            result = result_data['result']
            job_title = result_data['job_title']
            company = result_data['company']
            
            # Save outputs
            self.save_outputs(
                result['resume_text'],
                result['cover_letter'],
                job_title,
                company
            )
            
            # Clear fields
            self.clear_fields()
            
            self.status_label.config(text="Ready", foreground="green")
            messagebox.showinfo("Success", "Resume tailoring completed! Files saved to output folder.")
            self._log_message("Files saved successfully", "info")
            
        except Exception as e:
            self.status_label.config(text="Save failed", foreground="red")
            messagebox.showerror("Save Error", f"Error saving files: {e}")
            self._log_message(f"Save error: {e}", "error")
            return
        finally:
            self.set_ui_enabled(True)
    
    def _create_custom_prompt_tab(self):
        """Create the Custom Prompt Management tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Custom Prompts")
        
        # Instructions
        instruction_text = "Create custom prompt templates for specific roles or companies. Save them in prompts/user/ directory as .txt.j2 files. Available variables: role_level, company_name, job_title, job_description, resume_text"
        
        ttk.Label(tab, text=instruction_text, wraplength=600, justify=tk.LEFT).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=10)
        
        # Prompt name entry
        ttk.Label(tab, text="Prompt Name:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.prompt_name_entry = ttk.Entry(tab, width=40)
        self.prompt_name_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.prompt_name_entry.insert(0, "custom_")
        
        # Template editor
        ttk.Label(tab, text="Prompt Template:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.prompt_text = scrolledtext.ScrolledText(tab, width=80, height=20, wrap=tk.WORD)
        self.prompt_text.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Load default template
        try:
            with open("prompts/user/custom_template.txt.j2", "r") as f:
                self.prompt_text.insert("1.0", f.read())
        except:
            default_template = """# Custom Resume Tailoring Prompt Template
# Available variables: {{ role_level }}, {{ company_name }}, {{ job_title }}, {{ job_description }}, {{ resume_text }}

# INSTRUCTIONS:
# 1. Write your custom prompt below
# 2. Use the variables in {{ double_braces }} where appropriate
# 3. Save with a descriptive name
# 4. Use the Role Level dropdown to select this prompt when tailoring

# EXAMPLE CUSTOM PROMPT STRUCTURE:

You are an expert resume tailor specializing in {{ role_level }} positions for {{ company_name }}.

TASK: Tailor the following resume for the {{ job_title }} role.

Original Resume:
{{ resume_text }}

Job Description:
{{ job_title }} at {{ company_name }}
{{ job_description }}

Requirements:
1. Match language to job description keywords
2. Quantify achievements where possible
3. Emphasize relevant certifications and experience
4. Optimize for ATS (Applicant Tracking Systems)

Output ONLY the tailored resume text.

Write your custom prompt below...
"""
            self.prompt_text.insert("1.0", default_template)
        
        # Buttons
        button_frame = ttk.Frame(tab)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        save_button = ttk.Button(button_frame, text="Save Prompt", command=self.save_custom_prompt)
        save_button.grid(row=0, column=0, padx=5)
        
        load_button = ttk.Button(button_frame, text="Load Prompt", command=self.load_custom_prompt)
        load_button.grid(row=0, column=1, padx=5)
        
        clear_button = ttk.Button(button_frame, text="Clear", command=self.clear_prompt_editor)
        clear_button.grid(row=0, column=2, padx=5)
        
        # Make text area expandable
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(2, weight=1)
    
    def save_custom_prompt(self):
        """Save custom prompt template to file."""
        prompt_name = self.prompt_name_entry.get().strip()
        if not prompt_name.endswith('.txt.j2'):
            prompt_name += '.txt.j2'
        
        if not prompt_name or prompt_name == '.txt.j2':
            messagebox.showerror("Error", "Please enter a valid prompt name.")
            return
        
        template_content = self.prompt_text.get('1.0', tk.END).strip()
        
        try:
            with open(f"prompts/user/{prompt_name}", 'w') as f:
                f.write(template_content)
            messagebox.showinfo("Success", f"Prompt saved as {prompt_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save prompt: {e}")
    
    def load_custom_prompt(self):
        """Load custom prompt template using curated dropdown (Golden Rule #5 - Security)"""
        prompts_dir = Path("prompts/user")
        
        # Verify directory exists
        if not prompts_dir.exists():
            prompts_dir.mkdir(parents=True, exist_ok=True)
            messagebox.showwarning("No Prompts", "No custom prompts found. Created prompts/user/ directory. Please add .txt.j2 files.")
            self._log_message("Prompts directory created but empty", "warning")
            return
        
        # Get available prompts (no filesystem navigation - Golden Rule #5)
        try:
            available_prompts = [f.name for f in prompts_dir.glob("*.txt.j2")]
        except Exception as e:
            self._log_message(f"Error reading prompts directory: {e}", "error")
            messagebox.showerror("Error", f"Could not read prompts directory: {e}")
            return
        
        if not available_prompts:
            messagebox.showwarning("No Prompts", "No custom prompts found in prompts/user/. Please add .txt.j2 files.")
            self._log_message("No prompts available in prompts/user/", "warning")
            return
        
        # Create selection window (curated list - no file dialog)
        selection_window = tk.Toplevel(self.master)
        selection_window.title("Select Custom Prompt")
        selection_window.geometry("400x300")
        
        ttk.Label(selection_window, text="Available Prompts:", font=('Arial', 10, 'bold')).pack(pady=10)
        
        # Create listbox with available prompts
        listbox = tk.Listbox(selection_window, selectmode=tk.SINGLE, height=10, width=40)
        for prompt in sorted(available_prompts):
            listbox.insert(tk.END, prompt)
        listbox.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # Add selection button
        def select_prompt():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a prompt.")
                return
            
            prompt_name = listbox.get(selection[0])
            selection_window.destroy()
            
            # Load the selected prompt
            try:
                prompt_path = prompts_dir / prompt_name
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.prompt_name_entry.delete(0, tk.END)
                self.prompt_name_entry.insert(0, prompt_name.replace('.txt.j2', ''))
                
                self.prompt_text.delete('1.0', tk.END)
                self.prompt_text.insert("1.0", content)
                
                self._log_message(f"Loaded custom prompt: {prompt_name}", "info")
                messagebox.showinfo("Success", f"Loaded prompt: {prompt_name}")
                
            except Exception as e:
                self._log_message(f"Load prompt error: {e}", "error")
                messagebox.showerror("Error", f"Failed to load prompt: {e}")
        
        ttk.Button(selection_window, text="Load Selected", command=select_prompt).pack(pady=10)
    
    def clear_prompt_editor(self):
        """Clear the prompt editor fields"""
        self.prompt_name_entry.delete(0, tk.END)
        self.prompt_text.delete('1.0', tk.END)
        self._log_message("Cleared prompt editor", "info")
    
    def _create_tailored_docs_tab(self):
        """Create the Tailored Documents tab with split view for resume and cover letter"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Tailored Documents")
        
        # Title
        ttk.Label(tab, text="Tailored Resumes & Cover Letters", font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=10)
        
        # Applications list
        ttk.Label(tab, text="Select Application:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # Create treeview for applications
        columns = ('Job Title', 'Company', 'Date')
        self.applications_tree = ttk.Treeview(tab, columns=columns, show='headings', height=8)
        self.applications_tree.heading('Job Title', text='Job Title')
        self.applications_tree.heading('Company', text='Company')
        self.applications_tree.heading('Date', text='Date')
        
        self.applications_tree.column('Job Title', width=200)
        self.applications_tree.column('Company', width=200)
        self.applications_tree.column('Date', width=150)
        
        self.applications_tree.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.applications_tree.yview)
        self.applications_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
        
        # Bind selection event
        self.applications_tree.bind('<<TreeviewSelect>>', self._on_application_select)
        
        # Split view for resume and cover letter
        ttk.Label(tab, text="Tailored Resume", font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=(10, 5))
        ttk.Label(tab, text="Cover Letter", font=('Arial', 10, 'bold')).grid(row=3, column=1, sticky=tk.W, pady=(10, 5))
        
        # Text areas for resume and cover letter
        self.tailored_resume_text = scrolledtext.ScrolledText(tab, width=50, height=20, wrap=tk.WORD)
        self.tailored_resume_text.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5), pady=5)
        
        self.cover_letter_text = scrolledtext.ScrolledText(tab, width=50, height=20, wrap=tk.WORD)
        self.cover_letter_text.grid(row=4, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0), pady=5)
        
        # Buttons
        button_frame = ttk.Frame(tab)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.refresh_apps_button = ttk.Button(button_frame, text="Refresh Applications", command=self._refresh_applications_list)
        self.refresh_apps_button.grid(row=0, column=0, padx=5)
        
        self.export_pdf_button = ttk.Button(button_frame, text="Export as PDF", command=self._export_as_pdf, state='disabled')
        self.export_pdf_button.grid(row=0, column=1, padx=5)
        
        # Refresh applications list
        self._refresh_applications_list()
        
        # Configure grid weights
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(2, weight=1)
        tab.rowconfigure(4, weight=2)
    
    def _refresh_applications_list(self):
        """Refresh the applications list in treeview"""
        # Clear existing items
        for item in self.applications_tree.get_children():
            self.applications_tree.delete(item)
        
        # Load applications from database
        applications = self.db_manager.get_all_applications()
        for app in applications:
            # Format date
            created_at = datetime.strptime(app['created_at'], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d %H:%M')
            self.applications_tree.insert('', tk.END, values=(
                app['job_title'],
                app['company_name'],
                created_at
            ), iid=app['id'])
    
    def _on_application_select(self, event):
        """Handle application selection in treeview"""
        selection = self.applications_tree.selection()
        if selection:
            app_id = selection[0]
            # Get application details
            applications = self.db_manager.get_all_applications()
            selected_app = None
            for app in applications:
                if str(app['id']) == app_id:
                    selected_app = app
                    break
            
            if selected_app:
                # Load resume content
                try:
                    with open(selected_app['resume_path'], 'r', encoding='utf-8') as f:
                        resume_content = f.read()
                    self.tailored_resume_text.delete('1.0', tk.END)
                    self.tailored_resume_text.insert('1.0', resume_content)
                except Exception as e:
                    self.tailored_resume_text.delete('1.0', tk.END)
                    self.tailored_resume_text.insert('1.0', f"Error loading resume: {e}")
                
                # Load cover letter content
                try:
                    with open(selected_app['cover_letter_path'], 'r', encoding='utf-8') as f:
                        cover_letter_content = f.read()
                    self.cover_letter_text.delete('1.0', tk.END)
                    self.cover_letter_text.insert('1.0', cover_letter_content)
                except Exception as e:
                    self.cover_letter_text.delete('1.0', tk.END)
                    self.cover_letter_text.insert('1.0', f"Error loading cover letter: {e}")
                
                # Enable export button
                self.export_pdf_button.config(state='normal')
                self.current_selected_app = selected_app
            else:
                self.tailored_resume_text.delete('1.0', tk.END)
                self.cover_letter_text.delete('1.0', tk.END)
                self.export_pdf_button.config(state='disabled')
        else:
            self.tailored_resume_text.delete('1.0', tk.END)
            self.cover_letter_text.delete('1.0', tk.END)
            self.export_pdf_button.config(state='disabled')
    
    def _export_as_pdf(self):
        """Export current tailored documents as PDF"""
        if not hasattr(self, 'current_selected_app'):
            messagebox.showwarning("Export Error", "Please select an application first.")
            return
        
        try:
            # Import reportlab here to avoid issues if not installed
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            
            # Get job title and company for filename
            job_title = self.current_selected_app['job_title'].replace(' ', '_').replace('/', '_')
            company = self.current_selected_app['company_name'].replace(' ', '_').replace('/', '_')
            
            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=f"{company}_{job_title}_Application.pdf"
            )
            
            if not file_path:
                return
            
            # Create PDF document
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                alignment=TA_CENTER,
                fontSize=16,
                spaceAfter=30
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10
            )
            
            normal_style = styles['Normal']
            
            # Build document content
            story = []
            
            # Title
            title = Paragraph(f"Job Application Materials", title_style)
            story.append(title)
            
            # Job details
            job_info = Paragraph(f"<b>Position:</b> {self.current_selected_app['job_title']}<br/><b>Company:</b> {self.current_selected_app['company_name']}", normal_style)
            story.append(job_info)
            story.append(Spacer(1, 0.2*inch))
            
            # Tailored Resume
            story.append(Paragraph("Tailored Resume", heading_style))
            
            # Read resume content
            with open(self.current_selected_app['resume_path'], 'r', encoding='utf-8') as f:
                resume_content = f.read()
            
            # Add resume content
            resume_para = Paragraph(resume_content.replace('\n', '<br/>'), normal_style)
            story.append(resume_para)
            story.append(PageBreak())
            
            # Cover Letter
            story.append(Paragraph("Cover Letter", heading_style))
            
            # Read cover letter content
            with open(self.current_selected_app['cover_letter_path'], 'r', encoding='utf-8') as f:
                cover_letter_content = f.read()
            
            # Add cover letter content
            cover_letter_para = Paragraph(cover_letter_content.replace('\n', '<br/>'), normal_style)
            story.append(cover_letter_para)
            
            # Build PDF
            doc.build(story)
            
            messagebox.showinfo("PDF Export", f"Documents exported successfully to:\n{file_path}")
            self._log_message(f"PDF exported to: {file_path}", "info")
            
        except ImportError:
            messagebox.showerror("PDF Export Error", "ReportLab library not found. Please install it with: pip install reportlab")
            self._log_message("ReportLab not installed for PDF export", "error")
        except Exception as e:
            messagebox.showerror("PDF Export Error", f"Failed to export PDF: {str(e)}")
            self._log_message(f"PDF export error: {e}", "error")
    
    def save_outputs(self, tailored_resume, cover_letter, job_title, company):
        """Save tailored documents to output folder and show user where they are"""
        try:
            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_company = company.replace(" ", "_").replace("/", "_")
            safe_title = job_title.replace(" ", "_").replace("/", "_")
            
            # Create base filename
            base_name = f"{safe_company}_{safe_title}_{timestamp}"
            
            # Ensure output directory exists
            OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
            
            # Save tailored resume
            resume_path = OUTPUT_PATH / f"{base_name}_resume.txt"
            with open(resume_path, 'w', encoding='utf-8') as f:
                f.write(tailored_resume)
            
            # Save cover letter
            cover_letter_path = OUTPUT_PATH / f"{base_name}_cover_letter.txt"
            with open(cover_letter_path, 'w', encoding='utf-8') as f:
                f.write(cover_letter)
            
            # Add to database
            self.db_manager.add_application(
                job_title=job_title,
                company_name=company,
                job_url="",
                resume_path=str(resume_path),
                cover_letter_path=str(cover_letter_path)
            )
            
            # SHOW USER WHERE FILES ARE SAVED (Fix #2)
            messagebox.showinfo(
                "Files Saved Successfully",
                f"Tailored documents saved to:\n\n{OUTPUT_PATH}\n\n"
                f"Resume: {base_name}_resume.txt\n"
                f"Cover Letter: {base_name}_cover_letter.txt"
            )
            
            self._log_message(f"Files saved: {base_name}_*.txt", "info")
        except Exception as e:
            self._log_message(f"Error saving files: {e}", "error")
            raise
    
    def clear_fields(self):
        """Clear all input fields"""
        self.job_title_entry.delete(0, tk.END)
        self.company_entry.delete(0, tk.END)
        self.job_desc_text.delete('1.0', tk.END)
        self.job_url_entry.delete(0, tk.END)
    
    def set_ui_enabled(self, enabled):
        """Enable or disable UI elements during processing"""
        state = 'normal' if enabled else 'disabled'
        
        self.job_title_entry.config(state=state)
        self.company_entry.config(state=state)
        self.job_desc_text.config(state=state)
        self.job_url_entry.config(state=state)
        self.start_button.config(state=state)
        self.clear_button.config(state=state)
        self.upload_button.config(state=state)
        self.delete_button.config(state=state)
        self.set_active_button.config(state=state)
    
    def _show_tooltip(self, event, text):
        """Show tooltip with role definitions"""
        # Create tooltip window if it doesn't exist
        if not hasattr(self, '_tooltip_window') or not self._tooltip_window:
            self._tooltip_window = tk.Toplevel()
            self._tooltip_window.wm_overrideredirect(True)
            self._tooltip_window.configure(bg='lightyellow', relief='solid', borderwidth=1)
            
            # Create label for tooltip text
            tooltip_label = tk.Label(self._tooltip_window, text=text, 
                                   bg='lightyellow', fg='black', 
                                   font=('Arial', 9), justify=tk.LEFT, 
                                   padx=5, pady=3)
            tooltip_label.pack()
        
        # Position tooltip near mouse cursor
        x, y = event.x_root + 10, event.y_root + 10
        self._tooltip_window.wm_geometry(f"+{x}+{y}")
        self._tooltip_window.deiconify()
    
    def _hide_tooltip(self):
        """Hide tooltip window"""
        if hasattr(self, '_tooltip_window') and self._tooltip_window:
            self._tooltip_window.withdraw()
    
    def _log_message(self, message, level='info'):
        """Add message to log window"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level.upper()}: {message}\n"
        
        # Insert at end
        self.log_text.insert(tk.END, log_entry)
        
        # Auto-scroll to bottom
        self.log_text.see(tk.END)
        
        # Also log to console
        logging.log(getattr(logging, level.upper()), message)
    
    def _check_queue(self):
        """Check for messages from worker threads"""
        try:
            while True:
                data = self.tailoring_queue.get_nowait()
                if data:
                    self.on_tailoring_complete(data)
        except queue.Empty:
            pass
        
        # Check again in 100ms
        self.master.after(100, self._check_queue)
    
    def _check_api_key(self):
        """Check if Gemini API key is configured with robust path detection"""
        # Try multiple possible .env locations
        possible_paths = [
            Path(__file__).parent.parent / ".env",  # Development path
            Path.cwd() / ".env",                    # Current working directory
            Path.home() / ".job_application_bot.env",  # User home directory
        ]
        
        api_key = None
        for env_path in possible_paths:
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
                api_key = os.getenv("GEMINI_API_KEY")
                if api_key and api_key != "your_api_key_here":
                    self._log_message(f"API key loaded from {env_path}", "info")
                    return  # Success, exit early
        
        # If we get here, no valid API key found
        messagebox.showwarning(
            "API Key Missing",
            "Gemini API key not found. Please set GEMINI_API_KEY in one of these locations:\n\n"
            "1. Project root: job-application-bot/.env\n"
            "2. Current directory: ./.env\n"
            "3. Home directory: ~/.job_application_bot.env\n\n"
            "You can get a free API key from: https://makersuite.google.com/app/apikey "
        )
        self._log_message("API key missing - please configure .env file", "warning")

def main():
    """Main entry point for the application"""
    print("DEBUG: Starting application...")
    root = tk.Tk()
    print("DEBUG: Tk root created")
    app = JobAppTkinter(root)
    print("DEBUG: JobAppTkinter instantiated")
    root.mainloop()
    print("DEBUG: Main loop ended")

if __name__ == "__main__":
    try:
        print("DEBUG: Entering main execution")
        main()
        print("DEBUG: Exited main execution normally")
    except Exception as e:
        import traceback
        print(f"DEBUG: Exception in main: {e}")
        traceback.print_exc()
        input("Press Enter to continue...")
