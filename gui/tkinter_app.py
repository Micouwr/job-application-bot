"""
Tkinter GUI for the Job Application Bot.
Enhanced with resume upload, selection, and management.
"""

import sys
import threading
import tkinter as tk
import logging
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime
import shutil
import json
import csv
from typing import List, Dict, Any

# Add project root to path to allow direct execution
# Note: Assuming 'database.py' and 'main.py' are one directory up
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
except NameError:
    # Handle environment where __file__ is not defined (e.g., interactive console)
    sys.path.insert(0, str(Path("..").resolve()))

from database import JobDatabase
from main import JobApplicationBot

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class JobAppTkinter:
    """
    Main application window for the Job Application Bot, built with Tkinter.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Job Application Bot - AI Resume Tailorer")
        self.root.geometry("1400x900")

        # Initialize Bot and Database once (FIX 1)
        self.bot = JobApplicationBot()
        self.db = JobDatabase()

        # Initialize UI-related attributes early (FIX 4)
        self.current_resume_path = None
        self.status_var = tk.StringVar(value="Initializing...")
        self.resume_dir = Path("data/resumes")
        self.resume_dir.mkdir(exist_ok=True, parents=True)

        # Widgets to manage during tailoring (must be initialized to None first)
        self.tailor_button = None
        self.clear_button = None
        self.job_text = None
        self.resume_text = None
        self.save_output_button = None

        # Initialize UI first (critical for macOS - prevents dialog blocking)
        self._init_ui()
        
        # Then check for resume after a brief delay
        self.root.after(100, self._ensure_default_resume)

    def _ensure_default_resume(self):
        """Creates a default resume template if no resumes exist."""
        default_path = self.resume_dir / "default_resume.txt"

        # Check if ANY .txt resume exists
        if not list(self.resume_dir.glob("*.txt")):
            default_content = """YOUR NAME
Email: your.email@example.com
Phone: (123) 456-7890

PROFESSIONAL SUMMARY:
Senior IT Infrastructure Architect with extensive experience in cloud and AI governance.
Experienced in implementing robust governance frameworks and leveraging cloud platforms (AWS, Azure)
to drive business transformation. Holds a CompTIA A+ certification, specializing in AI solutions.

CORE SKILLS:
- AWS, Azure, Python
- AI Governance, Machine Learning Principles, NLP (Natural Language Processing)
- ITIL, CISSP, CompTIA A+, TWO AI CERTIFICATIONS (REDACTED FOR PRIVACY)

EXPERIENCE:
Company Name - IT Infrastructure Manager (2020-Present)
- Led cloud migration projects, resulting in 30% cost reduction.
- Designed and implemented AI governance framework, ensuring compliance and ethical use of AI models.
- Managed a team of 10 help desk and infrastructure specialists.

EDUCATION:
B.S. Computer Science, University Name

CERTIFICATIONS:
- AWS Solutions Architect
- ITIL v4
- CompTIA A+
- Advanced AI/ML Certification 1
- Advanced AI/ML Certification 2
"""
            default_path.write_text(default_content, encoding="utf-8")

            # Also set the default as the active resume
            active_path = self.resume_dir / "active_resume.txt"
            active_path.write_text(str(default_path.absolute()))
            self.current_resume_path = default_path

            messagebox.showinfo(
                "Welcome",
                "Created a default resume template. Note that I've added placeholders for your new AI certifications! Please update it in the 'Manage Resumes' tab."
            )

    def _init_ui(self):
        """Initializes the user interface."""
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook.Tab', font=('Arial', 11, 'bold'))
        style.configure('TButton', font=('Arial', 10))
        style.configure('Accent.TButton', foreground='white', background='#3498db', font=('Arial', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#2980b9')])
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))

        # Main container with tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Add Job & Tailor
        add_job_frame = ttk.Frame(notebook)
        notebook.add(add_job_frame, text="🎯 Tailor Application")
        self._create_add_job_tab(add_job_frame)

        # Tab 2: Resume Management
        resume_mgmt_frame = ttk.Frame(notebook)
        notebook.add(resume_mgmt_frame, text="📄 Manage Resumes")
        self._create_resume_mgmt_tab(resume_mgmt_frame)

        # Tab 3: View Jobs
        view_jobs_frame = ttk.Frame(notebook)
        notebook.add(view_jobs_frame, text="📋 View Applications")
        self._create_view_jobs_tab(view_jobs_frame)

        # Tab 4: Statistics
        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="📊 Statistics")
        self._create_stats_tab(stats_frame)

        # Status bar (uses the status_var created in __init__)
        self.status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_add_job_tab(self, parent):
        """Creates the 'Add Job & Tailor' tab."""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Resume selection display
        resume_select_frame = ttk.LabelFrame(main_frame, text="Selected Resume", padding="5")
        resume_select_frame.pack(fill=tk.X, pady=(0, 10))

        self.selected_resume_label = ttk.Label(
            resume_select_frame,
            text="Loading active resume...",
            foreground="gray",
            font=('Arial', 10, 'italic')
        )
        self.selected_resume_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        refresh_btn = ttk.Button(
            resume_select_frame,
            text="Refresh Active Resume",
            command=self._load_selected_resume
        )
        refresh_btn.pack(side=tk.RIGHT)

        # --- Center Frame: Split Inputs (Left) vs Outputs (Right) ---
        center_frame = ttk.Frame(main_frame)
        center_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Left Frame: Inputs
        input_frame = ttk.Frame(center_frame)
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Right Frame: Outputs
        right_frame = ttk.Frame(center_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # --- Resume Input (Left Side, Top) ---
        resume_input_frame = ttk.LabelFrame(input_frame, text="Active Resume Text (Editable)", padding="5")
        resume_input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.resume_text = tk.Text(resume_input_frame, wrap=tk.WORD, font=('Arial', 10))
        self.resume_text.pack(fill=tk.BOTH, expand=True)
        self.resume_text.insert("1.0", "Loading resume content...")

        # --- Job Description Input (Left Side, Bottom) ---
        job_frame = ttk.LabelFrame(input_frame, text="Job Description (Paste Here)", padding="5")
        job_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.job_text = tk.Text(job_frame, wrap=tk.WORD, font=('Arial', 10))
        self.job_text.pack(fill=tk.BOTH, expand=True)
        self.job_text.insert("1.0", "Paste the complete job description here...")

        # --- Tailored Resume Output (Right Side, Top) ---
        resume_out_frame = ttk.LabelFrame(right_frame, text="✨ Tailored Resume", padding="5")
        resume_out_frame.pack(fill=tk.BOTH, expand=True)

        self.tailored_resume_text = tk.Text(
            resume_out_frame, wrap=tk.WORD, font=('Arial', 10),
            bg='#f0f0f0', state=tk.DISABLED
        )
        self.tailored_resume_text.pack(fill=tk.BOTH, expand=True)

        # --- Cover Letter Output (Right Side, Bottom) ---
        cl_out_frame = ttk.LabelFrame(right_frame, text="✨ Cover Letter", padding="5")
        cl_out_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.cover_letter_text = tk.Text(
            cl_out_frame, wrap=tk.WORD, font=('Arial', 10),
            bg='#f0f0f0', state=tk.DISABLED
        )
        self.cover_letter_text.pack(fill=tk.BOTH, expand=True)

        # --- Action Buttons (Global Bottom) ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.tailor_button = ttk.Button(
            button_frame, text="🚀 Tailor Application", command=self.start_tailoring,
            style='Accent.TButton'
        )
        self.tailor_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(
            button_frame, text="🗑️ Clear All", command=self.clear_fields
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.save_output_button = ttk.Button(
            button_frame, text="💾 Save Outputs", command=self.save_outputs,
            state=tk.DISABLED
        )
        self.save_output_button.pack(side=tk.LEFT, padx=5)

        # Load current resume on startup
        self._load_selected_resume()

    def _create_resume_mgmt_tab(self, parent):
        """Creates the 'Resume Management' tab."""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Instructions
        instr_frame = ttk.Frame(main_frame)
        instr_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            instr_frame,
            text="Upload, select, and manage multiple resume versions. Only .txt files can be read by the AI bot.",
            font=('Arial', 10, 'italic'),
            foreground='blue'
        ).pack(side=tk.LEFT)

        # --- Controls ---
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        upload_btn = ttk.Button(
            control_frame, text="⬆️ Upload New Resume", command=self.upload_resume,
            style='Accent.TButton'
        )
        upload_btn.pack(side=tk.LEFT, padx=5)

        delete_btn = ttk.Button(
            control_frame, text="🗑️ Delete Selected", command=self.delete_selected_resume
        )
        delete_btn.pack(side=tk.LEFT, padx=5)

        set_active_btn = ttk.Button(
            control_frame, text="✅ Set as Active", command=self.set_active_resume
        )
        set_active_btn.pack(side=tk.LEFT, padx=5)

        # --- Resume List ---
        list_frame = ttk.LabelFrame(main_frame, text="Available Resumes (.txt)", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=False, side=tk.LEFT, padx=(0, 10)) # Do not expand list frame

        self.resume_listbox = tk.Listbox(
            list_frame, width=40, font=('Arial', 10), selectmode=tk.SINGLE
        )
        self.resume_listbox.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.resume_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.resume_listbox.configure(yscrollcommand=scrollbar.set)

        # --- Preview Pane ---
        preview_frame = ttk.LabelFrame(main_frame, text="Preview Content", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

        self.resume_preview = tk.Text(
            preview_frame, wrap=tk.WORD, font=('Arial', 9), bg='#f5f5f5'
        )
        self.resume_preview.pack(fill=tk.BOTH, expand=True)

        # Bind selection event
        self.resume_listbox.bind('<<ListboxSelect>>', self._on_resume_select)

        # Load resume list
        self._refresh_resume_list()

    def _load_selected_resume(self):
        """Loads the currently selected resume path and updates UI."""
        if not self.resume_text:
            # Widget not initialized yet, skip
            return

        try:
            active_path = self.resume_dir / "active_resume.txt"

            # 1. Determine the path of the active resume
            if active_path.exists():
                self.current_resume_path = Path(active_path.read_text().strip())
            else:
                # Default to first resume found
                resumes = list(self.resume_dir.glob("*.txt"))
                if resumes:
                    self.current_resume_path = resumes[0]
                    active_path.write_text(str(self.current_resume_path.absolute()))
                else:
                    self.current_resume_path = None

            # 2. Update UI with resume status and content
            if self.current_resume_path and self.current_resume_path.exists():
                display_name = self.current_resume_path.name

                # Update status label
                self.selected_resume_label.config(
                    text=f"✅ Active: {display_name}",
                    foreground="green",
                    font=('Arial', 10)
                )

                # Load content into the editable text widget on the main tab
                content = self.current_resume_path.read_text(encoding='utf-8')
                self.resume_text.delete("1.0", tk.END)
                self.resume_text.insert(tk.END, content)

                self.status_var.set(f"Active resume loaded: {display_name}")
            else:
                # Handle no resume state
                self.selected_resume_label.config(
                    text="❌ No active resume. Upload one in 'Manage Resumes' tab.",
                    foreground="red",
                    font=('Arial', 10, 'italic')
                )
                self.resume_text.delete("1.0", tk.END)
                self.resume_text.insert(tk.END, "No active resume. Please upload or set one in the 'Manage Resumes' tab.")
                self.status_var.set("Error: No active resume found.")

        except Exception as e:
            logging.error(f"Error loading selected resume: {e}")
            self.selected_resume_label.config(
                text=f"❌ Error loading resume: {e}",
                foreground="red"
            )
            self.status_var.set("Error during resume load.")

    def upload_resume(self):
        """Uploads a new resume file (TXT, DOCX, PDF) and converts non-TXT to TXT placeholder."""
        path = filedialog.askopenfilename(
            title="Upload Resume",
            filetypes=[
                ("Text Files", "*.txt"),
                ("PDF Files", "*.pdf"),
                ("All Files", "*.*")
            ],
        )
        if not path:
            return

        try:
            source = Path(path)
            
            # Handle PDF files
            if source.suffix.lower() == '.pdf':
                try:
                    import PyPDF2
                    with open(source, 'rb') as file:
                        reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() or ""
                    
                    # Save as .txt
                    dest = self.resume_dir / f"{source.stem}.txt"
                    # Handle duplicates
                    counter = 1
                    while dest.exists():
                        dest = self.resume_dir / f"{source.stem}_{counter}.txt"
                        counter += 1
                    
                    dest.write_text(text, encoding='utf-8')
                    messagebox.showinfo("Success", f"PDF converted and saved: {dest.name}")
                except ImportError:
                    messagebox.showerror("Missing Dependency", "PyPDF2 is not installed. Please install it with: pip install PyPDF2")
                    return
                except Exception as e:
                    messagebox.showerror("PDF Error", f"Failed to extract text from PDF: {e}")
                    return
            else:
                # For TXT files, just copy
                dest = self.resume_dir / f"{source.stem}.txt"
                # Handle duplicates
                counter = 1
                while dest.exists():
                    dest = self.resume_dir / f"{source.stem}_{counter}.txt"
                    counter += 1
                shutil.copy2(source, dest)
                
                # Basic content check
                content = dest.read_text(encoding='utf-8')
                if len(content) < 100:
                    messagebox.showwarning(
                        "Short Resume",
                        f"The uploaded resume '{dest.name}' appears very short. Please verify content for AI processing."
                    )
                messagebox.showinfo("Success", f"Resume uploaded: {dest.name}")

            self._refresh_resume_list()

        except Exception as e:
            logging.error(f"Failed to upload resume: {e}")
            messagebox.showerror("Upload Error", f"Failed to upload resume: {e}")

    def delete_selected_resume(self):
        """Deletes the selected resume file."""
        selection = self.resume_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a resume to delete.")
            return

        # Extract clean filename (remove emojis and markers)
        resume_name_full = self.resume_listbox.get(selection[0])
        resume_name = resume_name_full.replace('✅ ', '').replace(' (ACTIVE)', '')
        resume_path = self.resume_dir / resume_name

        if not resume_path.exists():
            messagebox.showerror("Error", "Selected file does not exist on disk.")
            return

        # Prevent deleting active resume
        if self.current_resume_path and resume_path.resolve() == self.current_resume_path.resolve():
            messagebox.showerror(
                "Cannot Delete",
                "This is the active resume. Please set another resume as active first."
            )
            return

        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete '{resume_name}'?\nThis cannot be undone."
        ):
            try:
                resume_path.unlink()
                self._refresh_resume_list()
                messagebox.showinfo("Deleted", f"Deleted: {resume_name}")
            except Exception as e:
                logging.error(f"Failed to delete resume: {e}")
                messagebox.showerror("Delete Error", f"Failed to delete: {e}")

    def set_active_resume(self):
        """Sets the selected resume as active for tailoring."""
        selection = self.resume_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a resume to activate.")
            return

        # Extract clean filename
        resume_name_full = self.resume_listbox.get(selection[0])
        resume_name = resume_name_full.replace('✅ ', '').replace(' (ACTIVE)', '')
        resume_path = self.resume_dir / resume_name

        try:
            active_path = self.resume_dir / "active_resume.txt"
            active_path.write_text(str(resume_path.absolute()))

            # Update internal state and UI
            self._load_selected_resume()
            self._refresh_resume_list()

            messagebox.showinfo(
                "Resume Activated",
                f"Active resume set to: {resume_name}"
            )
        except Exception as e:
            logging.error(f"Failed to set active resume: {e}")
            messagebox.showerror("Activation Error", f"Failed to set active resume: {e}")

    def _refresh_resume_list(self):
        """Refreshes the resume listbox."""
        self.resume_listbox.delete(0, tk.END)

        try:
            # Get all text resumes
            resumes = sorted(self.resume_dir.glob("*.txt"))

            if not resumes:
                self.resume_listbox.insert(tk.END, "No resumes found. Upload one!")
                return

            active_resume_name = self.current_resume_path.name if self.current_resume_path else ""

            for resume in resumes:
                display_name = resume.name
                if resume.name == active_resume_name:
                    display_name = f"✅ {resume.name} (ACTIVE)"
                    self.resume_listbox.insert(tk.END, display_name)
                    self.resume_listbox.itemconfig(tk.END, {'bg':'#e8f5e9', 'fg':'green'})
                else:
                    self.resume_listbox.insert(tk.END, display_name)

        except Exception as e:
            logging.error(f"Error loading resume list: {e}")
            self.resume_listbox.insert(tk.END, f"Error loading resumes: {e}")

    def _on_resume_select(self, event):
        """Preview selected resume in the preview pane."""
        selection = self.resume_listbox.curselection()
        if not selection:
            return

        # Extract clean filename
        resume_name_full = self.resume_listbox.get(selection[0])
        resume_name = resume_name_full.replace('✅ ', '').replace(' (ACTIVE)', '')

        resume_path = self.resume_dir / resume_name

        try:
            self.resume_preview.delete("1.0", tk.END)
            if resume_path.exists():
                content = resume_path.read_text(encoding='utf-8')
                preview = content[:2000] + ("\n\n... [TRUNCATED] ..." if len(content) > 2000 else "")
                self.resume_preview.insert(tk.END, preview)
            else:
                self.resume_preview.insert(tk.END, "File not found!")
        except Exception as e:
            logging.error(f"Error previewing file: {e}")
            self.resume_preview.insert(tk.END, f"Error loading file: {e}")

    def start_tailoring(self):
        """Starts the tailoring process in a new thread."""
        job_description = self.job_text.get("1.0", tk.END).strip()
        resume_text = self.resume_text.get("1.0", tk.END).strip() # Read from the active input field

        if not job_description or "paste the complete job description here..." in job_description.lower():
            messagebox.showwarning("Input Required", "Please paste a complete job description.")
            return

        if not self.current_resume_path or not self.current_resume_path.exists() or len(resume_text) < 100:
            messagebox.showerror(
                "Resume Error",
                "Active resume is missing or too short. Check 'Manage Resumes' tab."
            )
            return

        self.status_var.set("🤖 AI is tailoring your application. This may take a moment...")
        self.set_ui_enabled(False)

        # Thread the blocking operation
        threading.Thread(target=self.tailor_application_thread, daemon=True).start()

    def tailor_application_thread(self):
        """The actual tailoring process, run in a thread."""
        job_description = self.job_text.get("1.0", tk.END).strip()
        # Read resume text directly from the editable widget
        resume_text = self.resume_text.get("1.0", tk.END).strip()

        try:
            # 1. Simulate job creation (the bot handles the database interaction later)
            job = {
                "title": "Ad-Hoc Tailoring Job",
                "company": "User Input",
                "url": "",
                "description": job_description,
                "location": "N/A",
            }

            # 2. Call the full pipeline which handles matching and tailoring
            result = self.bot.process_and_tailor_from_gui(job, user_resume_text=resume_text)

            # Check for specific failure case from the AI/pipeline
            if not result.get("resume_text") or not result.get("cover_letter"):
                raise Exception("AI returned incomplete or empty tailoring results.")

            self.root.after(0, self.on_tailoring_complete, result, None)
        except Exception as e:
            logging.error(f"Tailoring Thread Error: {e}")
            self.root.after(0, self.on_tailoring_complete, None, e)

    def on_tailoring_complete(self, result, error):
        """Handles the completion of the tailoring process."""
        self.set_ui_enabled(True)

        # Clear previous outputs
        self.tailored_resume_text.config(state=tk.NORMAL)
        self.cover_letter_text.config(state=tk.NORMAL)
        self.tailored_resume_text.delete("1.0", tk.END)
        self.cover_letter_text.delete("1.0", tk.END)

        if error:
            messagebox.showerror("❌ Tailoring Error", f"Failed to tailor application:\n{error}")
            self.status_var.set("Tailoring failed. Check console for details.")

            # Re-disable outputs
            self.tailored_resume_text.config(state=tk.DISABLED)
            self.cover_letter_text.config(state=tk.DISABLED)
            self.save_output_button.config(state=tk.DISABLED)
            return

        # Enable save button
        self.save_output_button.config(state=tk.NORMAL)

        # Display results
        self.tailored_resume_text.insert(tk.END, result.get("resume_text", "No tailored resume generated."))
        self.cover_letter_text.insert(tk.END, result.get("cover_letter", "No cover letter generated."))

        # Finalize output states
        self.tailored_resume_text.config(state=tk.DISABLED)
        self.cover_letter_text.config(state=tk.DISABLED)

        self.status_var.set("✅ Application tailored successfully! Ready to save.")

        messagebox.showinfo(
            "Success",
            "Application tailored successfully!\n\nReview the outputs and save your documents."
        )

    def clear_fields(self):
        """Clears all input and output fields in the Tailor tab."""
        # Clear inputs
        self.job_text.delete("1.0", tk.END)
        self.job_text.insert("1.0", "Paste the complete job description here...")

        # Reload the active resume content to reset any temporary user edits
        self._load_selected_resume()

        # Clear outputs (must enable before clearing and disable after)
        self.tailored_resume_text.config(state=tk.NORMAL)
        self.tailored_resume_text.delete("1.0", tk.END)
        self.tailored_resume_text.config(state=tk.DISABLED)

        self.cover_letter_text.config(state=tk.NORMAL)
        self.cover_letter_text.delete("1.0", tk.END)
        self.cover_letter_text.config(state=tk.DISABLED)

        self.save_output_button.config(state=tk.DISABLED)
        self.status_var.set("Fields cleared. Ready.")

    def set_ui_enabled(self, enabled: bool):
        """Explicitly enables or disables key UI elements in the Tailor tab."""
        state = tk.NORMAL if enabled else tk.DISABLED

        # Tailor tab controls
        self.tailor_button.config(state=state)
        self.clear_button.config(state=state)
        self.job_text.config(state=state)
        self.resume_text.config(state=state)

        # Output save button depends on successful output generation
        if enabled:
            # Only enable save button if there is content
            has_output = self.tailored_resume_text.get("1.0", tk.END).strip()
            # If the output text widget is disabled, it will return an empty string, so we must check the state.
            # We assume if enabled is True, the next step will involve checking content.
            # For now, just rely on the on_tailoring_complete to set save_output_button state.
            pass

        # Save button state is managed by on_tailoring_complete, not here
        # self.save_output_button.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = JobAppTkinter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
