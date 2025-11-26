"""
Tkinter GUI for the Job Application Bot.
Enhanced with resume upload, selection, and management.
"""

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Add project root to path to allow direct execution
sys.path.insert(0, "..")
from database import JobDatabase
from main import JobApplicationBot


class JobAppTkinter:
    """
    Main application window for the Job Application Bot, built with Tkinter.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Job Application Bot - AI Resume Tailorer")
        self.root.geometry("1400x900")
        self.bot = JobApplicationBot()
        self.current_resume_path = None
        self.resume_dir = Path("data/resumes")
        self.resume_dir.mkdir(exist_ok=True)
        
        # Create default resume if none exists
        self._ensure_default_resume()
        
        self._init_ui()

    def _ensure_default_resume(self):
        """Creates a default resume template if no resumes exist."""
        default_path = self.resume_dir / "default_resume.txt"
        if not any(self.resume_dir.glob("*.txt")):
            default_content = """YOUR NAME
Email: your.email@example.com
Phone: (123) 456-7890

PROFESSIONAL SUMMARY:
Senior IT Infrastructure Architect with extensive experience in cloud and AI governance...

CORE SKILLS:
- AWS, Azure, Python
- ITIL, CISSP
- Help Desk Leadership

EXPERIENCE:
Company Name - IT Infrastructure Manager (2020-Present)
- Led cloud migration projects...
- Implemented AI governance framework...

EDUCATION:
B.S. Computer Science, University Name

CERTIFICATIONS:
- AWS Solutions Architect
- ITIL v4
"""
            default_path.write_text(default_content, encoding="utf-8")
            messagebox.showinfo(
                "Welcome", 
                "Created default resume template.\nPlease update it in the Resume Management tab."
            )

    def _init_ui(self):
        """Initializes the user interface."""
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook.Tab', font=('Arial', 11, 'bold'))
        style.configure('TButton', font=('Arial', 10))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))

        # Main container with tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Add Job & Tailor
        add_job_frame = ttk.Frame(notebook)
        notebook.add(add_job_frame, text="🎯 Tailor Application")
        self._create_add_job_tab(add_job_frame)

        # Tab 2: Resume Management (NEW)
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

        # Status bar
        self.status_var = tk.StringVar(value="Ready - Select a resume in Manage Resumes tab")
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
            text="No resume selected. Go to 'Manage Resumes' tab first.",
            foreground="red",
            font=('Arial', 10, 'italic')
        )
        self.selected_resume_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Refresh resume list
        refresh_btn = ttk.Button(
            resume_select_frame, 
            text="Refresh Resume List", 
            command=self._load_selected_resume
        )
        refresh_btn.pack(side=tk.RIGHT)

        # Split layout
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # --- Job Description Input ---
        job_frame = ttk.LabelFrame(left_frame, text="Job Description (Paste Here)", padding="5")
        job_frame.pack(fill=tk.BOTH, expand=True)
        
        self.job_text = tk.Text(job_frame, wrap=tk.WORD, height=20, font=('Arial', 10))
        self.job_text.pack(fill=tk.BOTH, expand=True)
        self.job_text.insert("1.0", "Paste the complete job description here...")

        # --- Action Buttons ---
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=10)

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

        # --- Tailored Resume Output ---
        resume_out_frame = ttk.LabelFrame(right_frame, text="✨ Tailored Resume", padding="5")
        resume_out_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tailored_resume_text = tk.Text(
            resume_out_frame, wrap=tk.WORD, height=20, font=('Arial', 10), 
            bg='#f0f0f0', state=tk.DISABLED
        )
        self.tailored_resume_text.pack(fill=tk.BOTH, expand=True)

        # --- Cover Letter Output ---
        cl_out_frame = ttk.LabelFrame(right_frame, text="✨ Cover Letter", padding="5")
        cl_out_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.cover_letter_text = tk.Text(
            cl_out_frame, wrap=tk.WORD, height=15, font=('Arial', 10), 
            bg='#f0f0f0', state=tk.DISABLED
        )
        self.cover_letter_text.pack(fill=tk.BOTH, expand=True)

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
            text="Upload, select, and manage multiple resume versions. The selected resume will be used for tailoring.",
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
        list_frame = ttk.LabelFrame(main_frame, text="Available Resumes", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0, 10))

        self.resume_listbox = tk.Listbox(
            list_frame, width=40, font=('Arial', 10), selectmode=tk.SINGLE
        )
        self.resume_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.resume_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.resume_listbox.configure(yscrollcommand=scrollbar.set)

        # --- Preview Pane ---
        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

        self.resume_preview = tk.Text(
            preview_frame, wrap=tk.WORD, font=('Arial', 9), bg='#f5f5f5'
        )
        self.resume_preview.pack(fill=tk.BOTH, expand=True)

        # Bind selection event
        self.resume_listbox.bind('<<ListboxSelect>>', self._on_resume_select)

        # Load resume list
        self._refresh_resume_list()

    def _create_view_jobs_tab(self, parent):
        """Creates the 'View Jobs' tab."""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=10, padx=10)

        ttk.Label(control_frame, text="Status Filter:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.filter_var = tk.StringVar(value="pending_review")
        filter_combo = ttk.Combobox(
            control_frame, 
            textvariable=self.filter_var,
            values=["all", "pending_review", "applied", "interview", "rejected"],
            state="readonly",
            width=15
        )
        filter_combo.pack(side=tk.LEFT, padx=(0, 10))
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_jobs())

        refresh_btn = ttk.Button(control_frame, text="🔄 Refresh", command=self.refresh_jobs)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        export_btn = ttk.Button(control_frame, text="📤 Export List", command=self.export_jobs)
        export_btn.pack(side=tk.LEFT, padx=5)

        self.jobs_text = scrolledtext.ScrolledText(
            parent, width=100, height=35, wrap=tk.WORD, font=('Arial', 9)
        )
        self.jobs_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        self.refresh_jobs()

    def _create_stats_tab(self, parent):
        """Creates the 'Statistics' tab."""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=10, padx=10)

        refresh_btn = ttk.Button(control_frame, text="🔄 Refresh Stats", command=self.refresh_stats)
        refresh_btn.pack(side=tk.LEFT)

        self.stats_text = scrolledtext.ScrolledText(
            parent, width=100, height=35, wrap=tk.WORD, font=('Arial', 10, 'bold')
        )
        self.stats_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        self.refresh_stats()

    def _load_selected_resume(self):
        """Loads the currently selected resume path and updates UI."""
        try:
            active_path = self.resume_dir / "active_resume.txt"
            if active_path.exists():
                self.current_resume_path = Path(active_path.read_text().strip())
            else:
                # Default to first resume found
                resumes = list(self.resume_dir.glob("*.txt"))
                if resumes:
                    self.current_resume_path = resumes[0]
                    active_path.write_text(str(self.current_resume_path))
                else:
                    self.current_resume_path = None

            if self.current_resume_path and self.current_resume_path.exists():
                display_name = self.current_resume_path.name
                self.selected_resume_label.config(
                    text=f"✅ Active: {display_name}",
                    foreground="green",
                    font=('Arial', 10)
                )
                # Load into text widget
                self.resume_text.delete("1.0", tk.END)
                self.resume_text.insert(tk.END, self.current_resume_path.read_text())
            else:
                self.selected_resume_label.config(
                    text="❌ No active resume. Upload one in 'Manage Resumes' tab.",
                    foreground="red",
                    font=('Arial', 10, 'italic')
                )
        except Exception as e:
            self.selected_resume_label.config(
                text=f"❌ Error loading resume: {e}",
                foreground="red"
            )

    def upload_resume(self):
        """Uploads a new resume file (TXT, DOCX, PDF)."""
        path = filedialog.askopenfilename(
            title="Upload Resume",
            filetypes=[
                ("Text Files", "*.txt"),
                ("Word Documents", "*.docx"),
                ("PDF Files", "*.pdf"),
                ("All Files", "*.*")
            ],
        )
        if not path:
            return

        try:
            import shutil
            from pathlib import Path
            
            source = Path(path)
            dest = self.resume_dir / source.name
            
            # Handle duplicates
            counter = 1
            while dest.exists():
                stem = source.stem
                dest = self.resume_dir / f"{stem}_{counter}{source.suffix}"
                counter += 1

            # Copy file
            shutil.copy2(source, dest)
            
            # If PDF/DOCX, create a note to manually extract text
            if dest.suffix.lower() in ['.pdf', '.docx']:
                txt_version = dest.with_suffix('.txt')
                note = f"NOTE: Original file is {dest.suffix.upper()}\nPlease extract text manually or paste content below.\n\n[PLACEHOLDER CONTENT]"
                txt_version.write_text(note)
                messagebox.showinfo(
                    "File Upload", 
                    f"Uploaded {dest.name}\n\n⚠️  Please create a .txt version with extracted text for AI processing."
                )
                self._refresh_resume_list()
            else:
                # Validate text resume
                content = dest.read_text(encoding='utf-8')
                if len(content) < 100:
                    messagebox.showwarning(
                        "Short Resume", 
                        "Resume appears very short. Please verify content."
                    )
                
                messagebox.showinfo("Success", f"Resume uploaded: {dest.name}")
                self._refresh_resume_list()

        except Exception as e:
            messagebox.showerror("Upload Error", f"Failed to upload resume: {e}")

    def delete_selected_resume(self):
        """Deletes the selected resume file."""
        selection = self.resume_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a resume to delete.")
            return

        resume_name = self.resume_listbox.get(selection[0])
        resume_path = self.resume_dir / resume_name
        
        # Prevent deleting active resume
        if self.current_resume_path and resume_path == self.current_resume_path:
            messagebox.showerror(
                "Cannot Delete", 
                "This is the active resume. Please select another resume first."
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
                messagebox.showerror("Delete Error", f"Failed to delete: {e}")

    def set_active_resume(self):
        """Sets the selected resume as active for tailoring."""
        selection = self.resume_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a resume to activate.")
            return

        resume_name = self.resume_listbox.get(selection[0])
        resume_path = self.resume_dir / resume_name
        
        try:
            active_path = self.resume_dir / "active_resume.txt"
            active_path.write_text(str(resume_path.absolute()))
            self.current_resume_path = resume_path
            
            # Update UI
            self._load_selected_resume()
            self._refresh_resume_list()
            
            messagebox.showinfo(
                "Resume Activated", 
                f"Active resume set to: {resume_name}"
            )
        except Exception as e:
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

            active_path = self.resume_dir / "active_resume.txt"
            active_resume = ""
            if active_path.exists():
                active_resume = Path(active_path.read_text().strip()).name

            for resume in resumes:
                display_name = resume.name
                if resume.name == active_resume:
                    display_name = f"✅ {resume.name} (ACTIVE)"
                    self.resume_listbox.insert(tk.END, display_name)
                    self.resume_listbox.itemconfig(tk.END, {'bg':'#e8f5e9', 'fg':'green'})
                else:
                    self.resume_listbox.insert(tk.END, display_name)

        except Exception as e:
            self.resume_listbox.insert(tk.END, f"Error loading resumes: {e}")

    def _on_resume_select(self, event):
        """Preview selected resume in the preview pane."""
        selection = self.resume_listbox.curselection()
        if not selection:
            return

        # Extract clean filename (remove emojis and markers)
        resume_name = self.resume_listbox.get(selection[0])
        resume_name = resume_name.replace('✅ ', '').replace(' (ACTIVE)', '')
        
        resume_path = self.resume_dir / resume_name
        
        try:
            self.resume_preview.delete("1.0", tk.END)
            if resume_path.exists():
                content = resume_path.read_text(encoding='utf-8')
                preview = content[:2000] + ("..." if len(content) > 2000 else "")
                self.resume_preview.insert(tk.END, preview)
            else:
                self.resume_preview.insert(tk.END, "File not found!")
        except Exception as e:
            self.resume_preview.insert(tk.END, f"Error loading file: {e}")

    def start_tailoring(self):
        """Starts the tailoring process in a new thread."""
        job_description = self.job_text.get("1.0", tk.END).strip()
        
        if not job_description or "paste a job description" in job_description.lower():
            messagebox.showwarning("Input Required", "Please paste a complete job description.")
            return

        if not self.current_resume_path or not self.current_resume_path.exists():
            messagebox.showerror(
                "No Resume", 
                "No active resume selected.\n\nPlease go to 'Manage Resumes' tab and upload/select a resume first."
            )
            return

        self.status_var.set("🤖 AI is tailoring your application...")
        self.set_ui_enabled(False)

        threading.Thread(target=self.tailor_application_thread, daemon=True).start()

    def tailor_application_thread(self):
        """The actual tailoring process, run in a thread."""
        job_description = self.job_text.get("1.0", tk.END).strip()
        resume_text = self.resume_text.get("1.0", tk.END).strip()

        try:
            # Create job object
            job = self.bot.scraper.add_manual_job(
                title="Job Application",
                company="N/A",
                url="",
                description=job_description,
                location="",
            )
            
            # Update status
            match = self.bot.matcher.match_job(job)
            
            # Tailor with current resume text
            result = self.bot.tailor.tailor_application(job, match, resume_text=resume_text)
            
            self.root.after(0, self.on_tailoring_complete, result, None)
        except Exception as e:
            self.root.after(0, self.on_tailoring_complete, None, e)

    def on_tailoring_complete(self, result, error):
        """Handles the completion of the tailoring process."""
        self.set_ui_enabled(True)
        if error:
            messagebox.showerror("❌ Tailoring Error", f"Failed to tailor application: {error}")
            self.status_var.set("Tailoring failed.")
            return

        # Enable save button
        self.save_output_button.config(state=tk.NORMAL)
        
        # Display results
        self.tailored_resume_text.config(state=tk.NORMAL)
        self.tailored_resume_text.delete("1.0", tk.END)
        self.tailored_resume_text.insert(tk.END, result.get("resume_text", ""))
        self.tailored_resume_text.config(state=tk.DISABLED)

        self.cover_letter_text.config(state=tk.NORMAL)
        self.cover_letter_text.delete("1.0", tk.END)
        self.cover_letter_text.insert(tk.END, result.get("cover_letter", ""))
        self.cover_letter_text.config(state=tk.DISABLED)

        self.status_var.set("✅ Application tailored successfully! Ready to save.")
        
        # Show success message
        messagebox.showinfo(
            "Success", 
            "Application tailored successfully!\n\nYou can now save the outputs or copy them manually."
        )

    def save_outputs(self):
        """Saves the tailored resume and cover letter to files."""
        try:
            job_title = "Tailored_Application"
            timestamp = self._get_timestamp()
            
            # Create output directory
            output_dir = Path("output") / f"{job_title}_{timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save resume
            resume_text = self.tailored_resume_text.get("1.0", tk.END).strip()
            if resume_text:
                resume_path = output_dir / "tailored_resume.txt"
                resume_path.write_text(resume_text, encoding='utf-8')
            
            # Save cover letter
            cover_text = self.cover_letter_text.get("1.0", tk.END).strip()
            if cover_text:
                cover_path = output_dir / "cover_letter.txt"
                cover_path.write_text(cover_text, encoding='utf-8')
            
            messagebox.showinfo(
                "Saved", 
                f"Files saved to:\n{output_dir}\n\nResume saved.\nCover letter saved."
            )
            self.status_var.set(f"📁 Saved to: {output_dir}")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save outputs: {e}")

    def refresh_jobs(self):
        """Refresh jobs list with filter."""
        self.jobs_text.delete("1.0", tk.END)

        try:
            with JobDatabase() as db:
                status_filter = self.filter_var.get()
                if status_filter == "all":
                    jobs = db.get_all_jobs()
                else:
                    jobs = db.get_jobs_by_status(status_filter)

            if not jobs:
                self.jobs_text.insert("1.0", f"No jobs found for filter: {status_filter}")
                return

            for i, job in enumerate(jobs, 1):
                self.jobs_text.insert(tk.END, f"{i}. {job['title']}\n")
                self.jobs_text.insert(tk.END, f"   Company: {job['company']}\n")
                self.jobs_text.insert(tk.END, f"   Status: {job['status']}\n")
                self.jobs_text.insert(tk.END, f"   Match: {job.get('match_score', 0)*100:.1f}%\n")
                self.jobs_text.insert(tk.END, f"   Location: {job.get('location', 'N/A')}\n")
                self.jobs_text.insert(tk.END, f"   URL: {job.get('url', 'N/A')}\n\n")

            self.status_var.set(f"Loaded {len(jobs)} jobs (filter: {status_filter})")

        except Exception as e:
            self.jobs_text.insert("1.0", f"Error loading jobs: {e}")
            self.status_var.set(f"Error: {e}")

    def refresh_stats(self):
        """Refresh statistics."""
        self.stats_text.delete("1.0", tk.END)

        try:
            with JobDatabase() as db:
                stats = db.get_statistics()

            self.stats_text.insert(tk.END, "📈 APPLICATION STATISTICS\n", "header")
            self.stats_text.insert(tk.END, f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
            
            self.stats_text.insert(tk.END, f"Total Jobs Processed: {stats['total_jobs']:,}\n", "highlight")
            self.stats_text.insert(tk.END, f"High Matches (≥80%): {stats['high_matches']:,}\n", "highlight")
            self.stats_text.insert(tk.END, f"Average Match Score: {stats['avg_match_score']*100:.1f}%\n\n", "highlight")

            self.stats_text.insert(tk.END, "📊 Applications by Status:\n", "header")
            for status, count in stats.get("by_status", {}).items():
                self.stats_text.insert(tk.END, f"  • {status.replace('_', ' ').title()}: {count:,}\n", "normal")

            self.stats_text.insert(tk.END, f"\n🏆 Success Rate: {stats.get('success_rate', 0)*100:.1f}%\n", "header")

            # Tag configurations for styling
            self.stats_text.tag_configure("header", font=('Arial', 11, 'bold'), foreground='#2c3e50')
            self.stats_text.tag_configure("highlight", font=('Arial', 10, 'bold'), foreground='#27ae60')
            self.stats_text.tag_configure("normal", font=('Arial', 10))

            self.status_var.set("Statistics refreshed")

        except Exception as e:
            self.stats_text.insert("1.0", f"Error loading stats: {e}")
            self.status_var.set(f"Error: {e}")

    def export_jobs(self):
        """Exports job list to file."""
        try:
            file_path = filedialog.asksaveasfilename(
                title="Export Job List",
                defaultextension=".csv",
                filetypes=[
                    ("CSV Files", "*.csv"),
                    ("JSON Files", "*.json"),
                    ("All Files", "*.*")
                ]
            )
            if not file_path:
                return

            with JobDatabase() as db:
                jobs = db.get_all_jobs()

            if file_path.endswith('.json'):
                import json
                with open(file_path, 'w') as f:
                    json.dump(jobs, f, indent=2, default=str)
            else:
                import csv
                with open(file_path, 'w', newline='') as f:
                    if jobs:
                        writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
                        writer.writeheader()
                        writer.writerows(jobs)

            messagebox.showinfo("Export Complete", f"Exported {len(jobs)} jobs to {file_path}")
            self.status_var.set(f"📤 Exported to {file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")

    def clear_fields(self):
        """Clears all input and output fields."""
        self.job_text.delete("1.0", tk.END)
        self.job_text.insert("1.0", "Paste the complete job description here...")

        self.tailored_resume_text.config(state=tk.NORMAL)
        self.tailored_resume_text.delete("1.0", tk.END)
        self.tailored_resume_text.config(state=tk.DISABLED)

        self.cover_letter_text.config(state=tk.NORMAL)
        self.cover_letter_text.delete("1.0", tk.END)
        self.cover_letter_text.config(state=tk.DISABLED)

        self.save_output_button.config(state=tk.DISABLED)
        self.status_var.set("Fields cleared. Ready.")

    def set_ui_enabled(self, enabled: bool):
        """Enables or disables the UI elements."""
        state = tk.NORMAL if enabled else tk.DISABLED
        for child in self.root.winfo_children():
            if isinstance(child, ttk.Notebook):
                for tab in child.winfo_children():
                    for widget in tab.winfo_children():
                        if isinstance(widget, (ttk.Button, ttk.Entry, tk.Text, ttk.Combobox)):
                            try:
                                widget.config(state=state)
                            except:
                                pass

    def _get_timestamp(self):
        """Returns a timestamp string for file naming."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    root = tk.Tk()
    app = JobAppTkinter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
