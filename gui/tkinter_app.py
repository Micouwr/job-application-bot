"""
Tkinter GUI for the Job Application Bot - Production Version
Enhanced with thread-safe operations and resume management
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
import queue
from typing import List, Dict, Any

import subprocess
import os

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from database import JobDatabase
from main import JobApplicationBot
from config.settings import USER_DATA_DIR, BASE_DIR
from document_parser import parse_document

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

class ProgressDialog(tk.Toplevel):
    """Modal progress dialog for long-running operations."""
    def __init__(self, parent, title="Processing..."):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.geometry("400x150")
        self.resizable(False, False)

        ttk.Label(self, text="Please wait...", font=("Arial", 12)).pack(pady=20)
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=350)
        self.progress.pack(pady=10)
        self.progress.start()

        self.center_on_parent(parent)

    def center_on_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def close(self):
        self.progress.stop()
        self.destroy()

class JobAppTkinter:
    """Main application window for the Job Application Bot."""
    
    def __init__(self, root: tk.Tk, bot: JobApplicationBot, db: JobDatabase):
        self.root = root
        self.bot = bot
        self.db = db
        self.root.title("Job Application Bot - AI Resume Tailorer")
        self.root.geometry("1400x900")

        # Thread-safe queue for AI results
        self.tailoring_queue = queue.Queue()
        self.progress_dialog = None

        # Widget references
        self.tailor_button = None
        self.clear_button = None
        self.job_text = None
        self.resume_text = None
        self.save_output_button = None
        self.tailored_resume_text = None
        self.cover_letter_text = None
        self.status_var = None

        # Resume management
        self.resume_dir = USER_DATA_DIR / "resumes"
        self.resume_dir.mkdir(exist_ok=True, parents=True)
        self.current_resume_path = None

        self._create_default_resume()
        self._init_ui()
        
        if sys.platform == "darwin":
            self.root.createcommand("tk::mac::ShowPreferences", self.open_preferences)

    def open_preferences(self):
        """Open .env file for editing."""
        env_path = USER_DATA_DIR / ".env"
        if not env_path.exists():
            shutil.copy(BASE_DIR / ".env.example", env_path)
        self._open_file_externally(env_path)

    def _open_file_externally(self, path):
        """Cross-platform way to open a file or directory."""
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", path], check=True)
            elif sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.run(["xdg-open", path], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            messagebox.showerror("Error", f"Could not open '{path}':\n{e}")
            logging.error(f"Failed to open external file/dir: {e}")

    def _create_default_resume(self):
        """Creates a default resume template if no resumes exist."""
        default_path = self.resume_dir / "default_resume.txt"
        if not any(self.resume_dir.glob("*.txt")):
            default_content = """[Your Name]
Email: [your.email@example.com]
Phone: [(123) 456-7890]

## PROFESSIONAL SUMMARY
A brief summary of your professional background and skills.

## CORE SKILLS
- Skill 1
- Skill 2
- Skill 3

## EXPERIENCE
**[Company Name]** - [Your Title] (YYYY-YYYY)
- Achievement or responsibility 1
- Achievement or responsibility 2

## EDUCATION
[Degree] - [University Name]

## CERTIFICATIONS
- [Certification Name]
"""
            default_path.write_text(default_content, encoding="utf-8")
            active_path = self.resume_dir / "active_resume.txt"
            active_path.write_text(str(default_path.resolve()))
            self.current_resume_path = default_path
            messagebox.showinfo(
                "Welcome",
                "Created a default resume template. Please update it in the 'Manage Resumes' tab.",
            )

    def _init_ui(self):
        """Initialize user interface with thread-safe components."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook.Tab", font=("Arial", 11, "bold"))
        style.configure("TButton", font=("Arial", 10))
        style.configure(
            "Accent.TButton",
            foreground="white",
            background="#3498db",
            font=("Arial", 10, "bold"),
        )
        style.map("Accent.TButton", background=[("active", "#2980b9")])
        style.configure("Header.TLabel", font=("Arial", 12, "bold"))

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        add_job_frame = ttk.Frame(notebook)
        notebook.add(add_job_frame, text="🎯 Tailor Application")
        self._create_add_job_tab(add_job_frame)

        resume_mgmt_frame = ttk.Frame(notebook)
        notebook.add(resume_mgmt_frame, text="📄 Manage Resumes")
        self._create_resume_mgmt_tab(resume_mgmt_frame)

        view_jobs_frame = ttk.Frame(notebook)
        notebook.add(view_jobs_frame, text="📋 View Applications")
        self._create_view_jobs_tab(view_jobs_frame)

        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="📊 Statistics")
        self._create_stats_tab(stats_frame)

        self.status_var = tk.StringVar(value="Ready - Check your active resume.")
        self.status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_add_job_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Resume selection frame
        resume_select_frame = ttk.LabelFrame(
            main_frame, text="Selected Resume", padding="5"
        )
        resume_select_frame.pack(fill=tk.X, pady=(0, 10))

        self.selected_resume_label = ttk.Label(
            resume_select_frame,
            text="Loading active resume...",
            foreground="gray",
            font=("Arial", 10, "italic"),
        )
        self.selected_resume_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        refresh_btn = ttk.Button(
            resume_select_frame,
            text="Refresh Active Resume",
            command=self._load_selected_resume,
        )
        refresh_btn.pack(side=tk.RIGHT)

        # Main content area
        center_frame = ttk.Frame(main_frame)
        center_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        input_frame = ttk.Frame(center_frame)
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_frame = ttk.Frame(center_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Resume input
        resume_input_frame = ttk.LabelFrame(
            input_frame, text="Active Resume Text (Editable)", padding="5"
        )
        resume_input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.resume_text = tk.Text(resume_input_frame, wrap=tk.WORD, font=("Arial", 10))
        self.resume_text.pack(fill=tk.BOTH, expand=True)
        self.resume_text.insert("1.0", "Loading resume content...")

        # Job description
        job_frame = ttk.LabelFrame(
            input_frame, text="Job Description (Paste Here)", padding="5"
        )
        job_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.job_text = tk.Text(job_frame, wrap=tk.WORD, font=("Arial", 10))
        self.job_text.pack(fill=tk.BOTH, expand=True)
        self.job_text.insert("1.0", "Paste the complete job description here...")

        # Tailored resume output
        resume_out_frame = ttk.LabelFrame(
            right_frame, text="✨ Tailored Resume", padding="5"
        )
        resume_out_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.tailored_resume_text = tk.Text(
            resume_out_frame, wrap=tk.WORD, font=("Arial", 10), bg="#f0f0f0"
        )
        self.tailored_resume_text.pack(fill=tk.BOTH, expand=True)
        self.tailored_resume_text.config(state=tk.DISABLED)

        # Cover letter output
        cl_out_frame = ttk.LabelFrame(right_frame, text="✨ Cover Letter", padding="5")
        cl_out_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.cover_letter_text = tk.Text(
            cl_out_frame, wrap=tk.WORD, font=("Arial", 10), bg="#f0f0f0"
        )
        self.cover_letter_text.pack(fill=tk.BOTH, expand=True)
        self.cover_letter_text.config(state=tk.DISABLED)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.tailor_button = ttk.Button(
            button_frame,
            text="🚀 Tailor Application",
            command=self.start_tailoring,
            style="Accent.TButton",
        )
        self.tailor_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(
            button_frame, text="🗑️ Clear All", command=self.clear_fields
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.save_output_button = ttk.Button(
            button_frame,
            text="💾 Save Outputs",
            command=self.save_outputs,
            state=tk.DISABLED,
        )
        self.save_output_button.pack(side=tk.LEFT, padx=5)

        self.save_as_template_var = tk.BooleanVar()
        self.save_as_template_check = ttk.Checkbutton(
            button_frame,
            text="Save tailored resume as new template",
            variable=self.save_as_template_var,
        )
        self.save_as_template_check.pack(side=tk.LEFT, padx=10)

        self._load_selected_resume()

    def _create_resume_mgmt_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            top_frame,
            text="Upload (.pdf, .docx, .txt), select, and manage resume versions.",
            font=("Arial", 10, "italic"),
            foreground="blue",
        ).pack(side=tk.LEFT)

        open_folder_btn = ttk.Button(
            top_frame,
            text="📂 Open Resume Folder",
            command=lambda: self._open_file_externally(self.resume_dir),
        )
        open_folder_btn.pack(side=tk.RIGHT)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        upload_btn = ttk.Button(
            control_frame,
            text="⬆️ Upload New Resume",
            command=self.upload_resume,
            style="Accent.TButton",
        )
        upload_btn.pack(side=tk.LEFT, padx=5)

        delete_btn = ttk.Button(
            control_frame,
            text="🗑️ Delete Selected",
            command=self.delete_selected_resume,
        )
        delete_btn.pack(side=tk.LEFT, padx=5)

        set_active_btn = ttk.Button(
            control_frame, text="✅ Set as Active", command=self.set_active_resume
        )
        set_active_btn.pack(side=tk.LEFT, padx=5)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.LabelFrame(
            content_frame, text="Available Resumes (.txt)", padding="5"
        )
        list_frame.pack(
            fill=tk.Y, expand=False, side=tk.LEFT, padx=(0, 10), anchor="n"
        )

        self.resume_listbox = tk.Listbox(
            list_frame, width=40, font=("Arial", 10), selectmode=tk.SINGLE
        )
        self.resume_listbox.pack(side=tk.LEFT, fill=tk.Y, expand=True)

        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.resume_listbox.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.resume_listbox.configure(yscrollcommand=scrollbar.set)

        preview_frame = ttk.LabelFrame(content_frame, text="Preview Content", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

        self.resume_preview = tk.Text(
            preview_frame, wrap=tk.WORD, font=("Arial", 9), bg="#f5f5f5"
        )
        self.resume_preview.pack(fill=tk.BOTH, expand=True)
        self.resume_preview.config(state=tk.DISABLED)

        self.resume_listbox.bind("<<ListboxSelect>>", self._on_resume_select)
        self._refresh_resume_list()

    def _create_view_jobs_tab(self, parent):
        main_pane = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_pane = ttk.Frame(main_pane)
        main_pane.add(top_pane, weight=3)

        control_frame = ttk.Frame(top_pane)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(control_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_jobs())

        refresh_btn = ttk.Button(
            control_frame, text="🔄 Refresh", command=self.refresh_jobs
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)
        export_btn = ttk.Button(
            control_frame, text="📤 Export to CSV", command=self.export_jobs
        )
        export_btn.pack(side=tk.LEFT, padx=5)

        tree_frame = ttk.Frame(top_pane)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("score", "status", "company", "title", "location")
        self.jobs_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse"
        )
        for col in columns:
            self.jobs_tree.heading(
                col, text=col.title(), command=lambda c=col: self._sort_tree(c, False)
            )
        self.jobs_tree.column("score", width=80, anchor=tk.CENTER)
        self.jobs_tree.column("status", width=120)
        self.jobs_tree.column("company", width=200)
        self.jobs_tree.column("title", width=300)
        self.jobs_tree.column("location", width=150)

        self.jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.jobs_tree.yview
        )
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.jobs_tree.configure(yscrollcommand=tree_scroll.set)
        self.jobs_tree.bind("<<TreeviewSelect>>", self._on_job_select)

        bottom_pane = ttk.Frame(main_pane)
        main_pane.add(bottom_pane, weight=2)

        details_frame = ttk.LabelFrame(
            bottom_pane, text="Application Details", padding="10"
        )
        details_frame.pack(fill=tk.BOTH, expand=True)

        details_controls = ttk.Frame(details_frame)
        details_controls.pack(fill=tk.X, pady=(0, 5))

        self.update_status_menu = ttk.Combobox(
            details_controls,
            values=[
                "pending_review",
                "applied",
                "interview_scheduled",
                "offer_received",
                "rejected",
                "archived",
            ],
            state="readonly",
            width=20,
        )
        self.update_status_menu.pack(side=tk.LEFT)

        update_btn = ttk.Button(
            details_controls,
            text="Update Status",
            command=self._update_job_status,
            state=tk.DISABLED,
        )
        self.update_status_btn = update_btn
        update_btn.pack(side=tk.LEFT, padx=10)

        self.job_details_text = scrolledtext.ScrolledText(
            details_frame, wrap=tk.WORD, font=("Arial", 9), state=tk.DISABLED
        )
        self.job_details_text.pack(fill=tk.BOTH, expand=True)

        self.refresh_jobs()

    def _create_stats_tab(self, parent):
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=10, padx=10)

        refresh_btn = ttk.Button(
            control_frame, text="🔄 Refresh Stats", command=self.refresh_stats
        )
        refresh_btn.pack(side=tk.LEFT)

        self.stats_text = scrolledtext.ScrolledText(
            parent,
            width=100,
            height=35,
            wrap=tk.WORD,
            font=("Arial", 10, "bold"),
            state=tk.DISABLED,
        )
        self.stats_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        self.refresh_stats()

    def _load_selected_resume(self):
        if not self.resume_text:
            return

        try:
            active_path_file = self.resume_dir / "active_resume.txt"
            if active_path_file.exists():
                self.current_resume_path = Path(active_path_file.read_text().strip())
            else:
                resumes = list(self.resume_dir.glob("*.txt"))
                if resumes:
                    self.current_resume_path = resumes[0]
                    active_path_file.write_text(str(self.current_resume_path.resolve()))
                else:
                    self.current_resume_path = None

            if self.current_resume_path and self.current_resume_path.exists():
                display_name = self.current_resume_path.name
                self.selected_resume_label.config(
                    text=f"✅ Active: {display_name}",
                    foreground="green",
                    font=("Arial", 10),
                )
                content = self.current_resume_path.read_text(encoding="utf-8")
                self.resume_text.delete("1.0", tk.END)
                self.resume_text.insert(tk.END, content)
                self.status_var.set(f"Active resume loaded: {display_name}")
            else:
                self.selected_resume_label.config(
                    text="❌ No active resume. Upload one in 'Manage Resumes' tab.",
                    foreground="red",
                    font=("Arial", 10, "italic"),
                )
                self.resume_text.delete("1.0", tk.END)
                self.resume_text.insert(
                    tk.END,
                    "No active resume. Please upload or set one in the 'Manage Resumes' tab.",
                )
                self.status_var.set("Error: No active resume found.")
        except Exception as e:
            logging.error(f"Error loading selected resume: {e}")
            self.selected_resume_label.config(
                text=f"❌ Error loading resume: {e}", foreground="red"
            )
            self.status_var.set("Error during resume load.")

    def upload_resume(self):
        path = filedialog.askopenfilename(
            title="Upload Resume",
            filetypes=[
                ("Resume Files", "*.pdf *.docx *.txt"),
                ("All Files", "*.*"),
            ],
        )
        if not path:
            return

        source = Path(path)
        try:
            extracted_text = parse_document(source)
            dest = self.resume_dir / f"{source.stem}.txt"
            counter = 1
            while dest.exists():
                dest = self.resume_dir / f"{source.stem}_{counter}.txt"
                counter += 1
            dest.write_text(extracted_text, encoding="utf-8")

            if len(extracted_text) < 100:
                messagebox.showwarning(
                    "Short Resume",
                    f"The imported resume '{dest.name}' seems short. Please verify its content.",
                )
            messagebox.showinfo(
                "Success",
                f"Resume '{source.name}' was successfully imported as '{dest.name}'.",
            )
            self._refresh_resume_list()
        except Exception as e:
            logging.error(f"Failed to upload and process resume: {e}")
            messagebox.showerror("Upload Error", f"Failed to process the file: {e}")

    def delete_selected_resume(self):
        selection = self.resume_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a resume to delete.")
            return

        resume_name_full = self.resume_listbox.get(selection[0])
        resume_name = resume_name_full.replace("✅ ", "").replace(" (ACTIVE)", "")
        resume_path = self.resume_dir / resume_name

        if not resume_path.exists():
            messagebox.showerror("Error", "Selected file does not exist.")
            return

        if (
            self.current_resume_path
            and resume_path.resolve() == self.current_resume_path.resolve()
        ):
            messagebox.showerror(
                "Cannot Delete",
                "This is the active resume. Please set another as active first.",
            )
            return

        if messagebox.askyesno(
            "Confirm Delete", f"Permanently delete '{resume_name}'?"
        ):
            try:
                resume_path.unlink()
                self._refresh_resume_list()
                messagebox.showinfo("Deleted", f"Deleted: {resume_name}")
            except Exception as e:
                logging.error(f"Failed to delete resume: {e}")
                messagebox.showerror("Delete Error", f"Failed to delete: {e}")

    def set_active_resume(self):
        selection = self.resume_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a resume to activate.")
            return

        resume_name_full = self.resume_listbox.get(selection[0])
        resume_name = resume_name_full.replace("✅ ", "").replace(" (ACTIVE)", "")
        resume_path = self.resume_dir / resume_name

        try:
            active_path_file = self.resume_dir / "active_resume.txt"
            active_path_file.write_text(str(resume_path.resolve()))
            self._load_selected_resume()
            self._refresh_resume_list()
            messagebox.showinfo("Resume Activated", f"Active resume: {resume_name}")
        except Exception as e:
            logging.error(f"Failed to set active resume: {e}")
            messagebox.showerror("Activation Error", f"Failed to set active resume: {e}")

    def _refresh_resume_list(self):
        self.resume_listbox.delete(0, tk.END)
        try:
            resumes = sorted(self.resume_dir.glob("*.txt"))
            if not resumes:
                self.resume_listbox.insert(tk.END, "No resumes found. Upload one!")
                return

            active_name = self.current_resume_path.name if self.current_resume_path else ""
            for resume in resumes:
                display_name = resume.name
                if resume.name == active_name:
                    display_name = f"✅ {resume.name} (ACTIVE)"
                    self.resume_listbox.insert(tk.END, display_name)
                    self.resume_listbox.itemconfig(tk.END, {"bg": "#e8f5e9", "fg": "green"})
                else:
                    self.resume_listbox.insert(tk.END, display_name)
        except Exception as e:
            logging.error(f"Error loading resume list: {e}")
            self.resume_listbox.insert(tk.END, f"Error loading resumes: {e}")

    def _on_resume_select(self, event):
        selection = self.resume_listbox.curselection()
        if not selection:
            return

        resume_name_full = self.resume_listbox.get(selection[0])
        resume_name = resume_name_full.replace("✅ ", "").replace(" (ACTIVE)", "")
        resume_path = self.resume_dir / resume_name

        self.resume_preview.config(state=tk.NORMAL)
        self.resume_preview.delete("1.0", tk.END)
        try:
            if resume_path.exists():
                content = resume_path.read_text(encoding="utf-8")
                preview = content[:2000] + ("\n\n... [TRUNCATED] ..." if len(content) > 2000 else "")
                self.resume_preview.insert(tk.END, preview)
            else:
                self.resume_preview.insert(tk.END, "File not found!")
        except Exception as e:
            logging.error(f"Error previewing file: {e}")
            self.resume_preview.insert(tk.END, f"Error loading file: {e}")
        finally:
            self.resume_preview.config(state=tk.DISABLED)

    # --- Thread-Safe Tailoring Operations ---
    
    def start_tailoring(self):
        """Start tailoring in a background thread (main thread only)"""
        job_description = self.job_text.get("1.0", tk.END).strip()
        resume_text = self.resume_text.get("1.0", tk.END).strip()

        if not job_description or "paste the complete job description" in job_description.lower():
            messagebox.showwarning("Input Required", "Please paste a job description.")
            return

        if not self.current_resume_path or len(resume_text) < 100:
            messagebox.showerror("Resume Error", "Active resume is missing or too short.")
            return

        self.status_var.set("🤖 AI is tailoring your application...")
        self.set_ui_enabled(False)
        self.progress_dialog = ProgressDialog(self.root, "Tailoring Application")

        # Pass data to thread - do NOT access GUI from thread
        thread_data = {
            'job_description': job_description,
            'resume_text': resume_text,
            'bot': self.bot
        }
        
        threading.Thread(
            target=self._worker_thread,
            args=(thread_data, self.tailoring_queue),
            daemon=True,
        ).start()

        self.root.after(100, self._process_queue)

    def _worker_thread(self, data: dict, result_queue: queue.Queue):
        """Background worker - NO GUI ACCESS HERE"""
        try:
            result = data['bot'].tailor_for_gui(
                data['job_description'], 
                data['resume_text']
            )
            if not result or not result.get("resume_text"):
                raise ValueError("AI returned incomplete results.")
            result_queue.put(('success', result))
        except Exception as e:
            logging.error(f"Worker thread error: {e}", exc_info=True)
            result_queue.put(('error', str(e)))

    def _process_queue(self):
        """Process results from worker thread (main thread only)"""
        try:
            status, data = self.tailoring_queue.get_nowait()
            
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            self.set_ui_enabled(True)
            
            if status == 'success':
                self._update_gui_with_results(data)
            elif status == 'error':
                self._show_error(data)
            
        except queue.Empty:
            # Check again later
            self.root.after(100, self._process_queue)

    def _update_gui_with_results(self, result: dict):
        """Update GUI with tailoring results"""
        self.save_output_button.config(state=tk.NORMAL)
        
        for widget in [self.tailored_resume_text, self.cover_letter_text]:
            widget.config(state=tk.NORMAL)
            widget.delete("1.0", tk.END)

        self.tailored_resume_text.insert(
            tk.END, result.get("resume_text", "No resume generated.")
        )
        self.cover_letter_text.insert(
            tk.END, result.get("cover_letter", "No cover letter generated.")
        )
        
        for widget in [self.tailored_resume_text, self.cover_letter_text]:
            widget.config(state=tk.DISABLED)

        self.status_var.set("✅ Application tailored successfully!")
        messagebox.showinfo("Success", "Application tailored! Review and save.")

    def _show_error(self, error_msg: str):
        """Show error dialog"""
        messagebox.showerror("❌ Tailoring Error", f"Failed to tailor application:\n{error_msg}")
        self.status_var.set("Tailoring failed. Check logs.")

    def save_outputs(self):
        self.tailored_resume_text.config(state=tk.NORMAL)
        resume_content = self.tailored_resume_text.get("1.0", tk.END).strip()
        self.tailored_resume_text.config(state=tk.DISABLED)

        self.cover_letter_text.config(state=tk.NORMAL)
        cover_content = self.cover_letter_text.get("1.0", tk.END).strip()
        self.cover_letter_text.config(state=tk.DISABLED)

        if not resume_content and not cover_content:
            messagebox.showwarning("No Output", "No content to save.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Application As",
            defaultextension=".docx",
            filetypes=[
                ("Word Document", "*.docx"),
                ("PDF Document", "*.pdf"),
                ("Text File", "*.txt"),
            ],
        )
        if not file_path:
            return

        try:
            if self.save_as_template_var.get():
                template_name = f"tailored_{Path(file_path).stem}.txt"
                template_path = self.resume_dir / template_name
                template_path.write_text(resume_content, encoding="utf-8")
                self._refresh_resume_list()
                messagebox.showinfo(
                    "Template Saved", f"Saved as new template: {template_name}"
                )

            path = Path(file_path)
            if path.suffix.lower() == ".docx":
                import docx as python_docx
                doc = python_docx.Document()
                doc.add_heading("Tailored Resume", level=1)
                doc.add_paragraph(resume_content)
                doc.add_page_break()
                doc.add_heading("Cover Letter", level=1)
                doc.add_paragraph(cover_content)
                doc.save(path)
            elif path.suffix.lower() == ".pdf":
                self._save_as_pdf(path, resume_content, cover_content)
            else:  # .txt
                full_content = (
                    f"--- TAILORED RESUME ---\n\n{resume_content}\n\n"
                    f"--- COVER LETTER ---\n\n{cover_content}"
                )
                path.write_text(full_content, encoding="utf-8")

            messagebox.showinfo(
                "Saved", f"Application saved successfully to:\n{path.resolve()}"
            )
            self.status_var.set(f"📁 Saved to: {path.name}")

        except Exception as e:
            logging.error(f"Save outputs error: {e}", exc_info=True)
            messagebox.showerror("Save Error", f"Failed to save outputs: {e}")

    def _save_as_pdf(self, file_path, resume_text, cover_letter_text):
        doc = SimpleDocTemplate(str(file_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        resume_content = resume_text.replace("\n", "<br/>")
        cover_letter_content = cover_letter_text.replace("\n", "<br/>")

        story.append(Paragraph("Tailored Resume", styles["h1"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(resume_content, styles["Normal"]))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph("Cover Letter", styles["h1"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(cover_letter_content, styles["Normal"]))

        doc.build(story)

    def refresh_jobs(self):
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)

        search_term = self.search_var.get().lower()
        try:
            jobs = self.db.get_all_jobs()
            if search_term:
                jobs = [
                    j
                    for j in jobs
                    if search_term in j.get("title", "").lower()
                    or search_term in j.get("company", "").lower()
                ]

            for job in jobs:
                values = (
                    f"{job.get('match_score', 0) * 100:.1f}%",
                    job.get("status", "N/A").replace("_", " ").title(),
                    job.get("company", "N/A"),
                    job.get("title", "N/A"),
                    job.get("location", "N/A"),
                )
                self.jobs_tree.insert("", tk.END, values=values, iid=job.get("id"))
            self.status_var.set(f"Loaded {len(jobs)} jobs.")
        except Exception as e:
            logging.error(f"Error loading jobs: {e}")
            messagebox.showerror("Database Error", f"Could not load jobs: {e}")
        finally:
            self._on_job_select(None)

    def _sort_tree(self, col, reverse):
        """Sort treeview contents when a column header is clicked."""
        data = [
            (self.jobs_tree.set(child, col), child)
            for child in self.jobs_tree.get_children("")
        ]
        if col == "score":
            data.sort(key=lambda t: float(t[0].replace("%", "")), reverse=reverse)
        else:
            data.sort(reverse=reverse)

        for index, (val, child) in enumerate(data):
            self.jobs_tree.move(child, "", index)
        self.jobs_tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    def _on_job_select(self, event):
        selection = self.jobs_tree.selection()
        if not selection:
            self.job_details_text.config(state=tk.NORMAL)
            self.job_details_text.delete("1.0", tk.END)
            self.job_details_text.config(state=tk.DISABLED)
            self.update_status_btn.config(state=tk.DISABLED)
            self.update_status_menu.set("")
            return

        job_id = selection[0]
        try:
            job = self.db.get_job_by_id(job_id)
            if not job:
                return

            self.job_details_text.config(state=tk.NORMAL)
            self.job_details_text.delete("1.0", tk.END)
            details = (
                f"Company: {job.get('company', 'N/A')}\n"
                f"Title: {job.get('title', 'N/A')}\n"
                f"Status: {job.get('status', 'N/A')}\n"
                f"Score: {job.get('match_score', 0) * 100:.1f}%\n"
                f"URL: {job.get('url', 'N/A')}\n\n"
                f"--- DESCRIPTION ---\n{job.get('description', 'N/A')}"
            )
            self.job_details_text.insert("1.0", details)
            self.job_details_text.config(state=tk.DISABLED)

            self.update_status_btn.config(state=tk.NORMAL)
            self.update_status_menu.set(job.get("status", ""))
        except Exception as e:
            logging.error(f"Error fetching job details: {e}")

    def _update_job_status(self):
        selection = self.jobs_tree.selection()
        if not selection:
            return

        job_id = selection[0]
        new_status = self.update_status_menu.get()
        if not new_status:
            messagebox.showwarning("No Status", "Please select a new status.")
            return

        try:
            self.db.update_job_status(job_id, new_status)
            self.refresh_jobs()
            messagebox.showinfo(
                "Success", f"Updated job status to '{new_status.title()}'."
            )
        except Exception as e:
            logging.error(f"Failed to update status: {e}")
            messagebox.showerror("Update Error", f"Could not update status: {e}")

    def refresh_stats(self):
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)

        try:
            stats = self.db.get_statistics()
            stats_content = (
                "📈 APPLICATION STATISTICS\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Total Jobs Processed: {stats['total_jobs']:,}\n"
                f"High Matches (≥80%): {stats['high_matches']:,}\n"
                f"Average Match Score: {stats['avg_match_score']*100:.1f}%\n\n"
                "📊 Applications by Status:\n"
            )
            for status, count in stats.get("by_status", {}).items():
                stats_content += f"  • {status.replace('_', ' ').title()}: {count:,}\n"

            stats_content += "\n--- Recent Activity ---\n"
            if stats["recent_activity"]:
                for log in stats["recent_activity"]:
                    ts_str = (
                        log["timestamp"].strftime("%Y-%m-%d %H:%M")
                        if isinstance(log["timestamp"], datetime)
                        else str(log["timestamp"])
                    )
                    stats_content += (
                        f"[{ts_str}] Job {log.get('job_id', 'N/A')}: "
                        f"{log['action']} - {log['details']}\n"
                    )
            else:
                stats_content += "No recent activity.\n"

            self.stats_text.insert(tk.END, stats_content)
            self.status_var.set("Statistics refreshed")
        except Exception as e:
            logging.error(f"Error loading stats: {e}")
            self.stats_text.insert(tk.END, f"Error loading stats: {e}")
        finally:
            self.stats_text.config(state=tk.DISABLED)

    def export_jobs(self):
        file_path = filedialog.asksaveasfilename(
            title="Export Job List to CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not file_path:
            return
        try:
            jobs = self.db.get_all_jobs()
            if not jobs:
                messagebox.showinfo("No Data", "No jobs to export.")
                return

            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
                writer.writeheader()
                writer.writerows(jobs)
            messagebox.showinfo(
                "Export Complete", f"Exported {len(jobs)} jobs to {file_path}"
            )
        except Exception as e:
            logging.error(f"Export error: {e}")
            messagebox.showerror("Export Error", f"Failed to export: {e}")

    def clear_fields(self):
        self.job_text.delete("1.0", tk.END)
        self.job_text.insert("1.0", "Paste the complete job description here...")
        self._load_selected_resume()

        for widget in [self.tailored_resume_text, self.cover_letter_text]:
            widget.config(state=tk.NORMAL)
            widget.delete("1.0", tk.END)
            widget.config(state=tk.DISABLED)

        self.save_output_button.config(state=tk.DISABLED)
        self.status_var.set("Fields cleared. Ready.")

    def set_ui_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        widgets = [
            self.tailor_button,
            self.clear_button,
            self.job_text,
            self.resume_text,
        ]
        for widget in widgets:
            if widget:
                widget.config(state=state)

        if not enabled and self.save_output_button:
            self.save_output_button.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    db = JobDatabase()
    bot = JobApplicationBot(db=db, resume_path=Path("dummy.txt"))
    app = JobAppTkinter(root, bot, db)
    root.mainloop()


if __name__ == "__main__":
    main()
