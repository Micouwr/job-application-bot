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

from config.settings import OUTPUT_PATH, DB_PATH
from database import DatabaseManager
from tailor import process_and_tailor_from_gui
from models.resume_model import ResumeModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class JobAppTkinter:
    def __init__(self, master=None):
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
        
        # Create tabs
        self._create_add_job_tab()
        self._create_resume_mgmt_tab()
        self._create_output_tab()
        
        # Make notebook expandable
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
    
    def _create_add_job_tab(self):
        """Create the Add Job Application tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Add Job Application")
        
        # Job Details Section
        ttk.Label(tab, text="Job Title:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.job_title_entry = ttk.Entry(tab, width=50)
        self.job_title_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(tab, text="Company:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.company_entry = ttk.Entry(tab, width=50)
        self.company_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(tab, text="Job Description:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.job_desc_text = scrolledtext.ScrolledText(tab, width=80, height=15, wrap=tk.WORD)
        self.job_desc_text.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        ttk.Label(tab, text="Job URL:", font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.job_url_entry = ttk.Entry(tab, width=50)
        self.job_url_entry.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Buttons
        button_frame = ttk.Frame(tab)
        button_frame.grid(row=4, column=0, columnspan=4, pady=10)
        
        self.clear_button = ttk.Button(button_frame, text="Clear Fields", command=self.clear_fields)
        self.clear_button.grid(row=0, column=0, padx=5)
        
        self.start_button = ttk.Button(button_frame, text="Start Tailoring", command=self.start_tailoring)
        self.start_button.grid(row=0, column=1, padx=5)
        
        self.quit_button = ttk.Button(button_frame, text="Quit", command=self.master.quit)
        self.quit_button.grid(row=0, column=2, padx=5)
        
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
                except Exception as e:
                    self._log_message(f"PDF processing error: {e}", "error")
                    return
            
            # Add to database
            self.resume_model.add_resume(file_path, name, is_active=False)
            self._refresh_resume_list()
            self._log_message(f"Resume uploaded successfully: {name}", "success")
            
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
            
            self._log_message("Resume deleted successfully", "success")
            
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
            
            self._log_message(f"Active resume set to: {item['values'][0]}", "success")
            
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
    
    def start_tailoring(self):
        """Start the tailoring process"""
        # Get input values
        job_title = self.job_title_entry.get().strip()
        company = self.company_entry.get().strip()
        job_description = self.job_desc_text.get('1.0', tk.END).strip()
        job_url = self.job_url_entry.get().strip()
        
        # Validate inputs
        if not job_description:
            messagebox.showwarning("Missing Information", "Please fill in Job Title, Company, and Job Description")
            return
        
        # Load resume
        resume_text = self._load_selected_resume()
        if not resume_text:
            return
        
        # Disable UI during processing
        self.set_ui_enabled(False)
        self._log_message("Starting resume tailoring process...", "info")
        
        # Start tailoring thread
        thread = threading.Thread(
            target=self.tailor_application_thread,
            args=(job_title, company, job_description, job_url, resume_text)
        )
        thread.daemon = True
        thread.start()
    
    def tailor_application_thread(self, job_title, company, job_description, job_url, resume_text):
        """Thread function for tailoring process"""
        try:
            # Process and tailor
            result = process_and_tailor_from_gui(
                job_title=job_title,
                company=company,
                job_description=job_description,
                job_url=job_url,
                resume_text=resume_text,
                applicant_name="Michelle Nicole"
            )
            
            # Check for required fields
            if not result or not result.get("resume_text") or not result.get("cover_letter"):
                raise Exception("AI returned incomplete or empty tailoring results")
            
            # Log success
            self._log_message("Resume tailoring completed successfully", "success")
            
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
            
            messagebox.showinfo("Success", "Resume tailoring completed! Files saved to output folder.")
            self._log_message("Files saved successfully", "success")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving files: {e}")
            self._log_message(f"Save error: {e}", "error")
        finally:
            self.set_ui_enabled(True)
    
    def save_outputs(self, tailored_resume, cover_letter, job_title, company):
        """Save tailored documents to output folder"""
        # Create timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_company = company.replace(" ", "_").replace("/", "_")
        safe_title = job_title.replace(" ", "_").replace("/", "_")
        
        # Create base filename
        base_name = f"{safe_company}_{safe_title}_{timestamp}"
        
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
        
        self._log_message(f"Files saved: {base_name}_*.txt", "info")
    
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
        """Check if Gemini API key is configured"""
        load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key or api_key == "your_api_key_here":
            messagebox.showwarning(
                "API Key Missing",
                "Gemini API key not found. Please set GEMINI_API_KEY in your .env file.\n\n"
                "You can get a free API key from: https://makersuite.google.com/app/apikey"
            )
            self._log_message("API key missing - please configure .env file", "warning")

def main():
    """Main entry point for the application"""
    root = tk.Tk()
    app = JobAppTkinter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
