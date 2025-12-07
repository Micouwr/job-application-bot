# app/gui.py - Threaded, safe, professional GUI (no freezing)

import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, ttk
import logging
import threading
import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List

# Import core application logic
try:
    from .bot import JobApplicationBot
    from .config import config
    from .utils import extract_text_from_file, generate_pdf_from_markdown
except ImportError:
    from bot import JobApplicationBot
    from config import config
    from utils import extract_text_from_file, generate_pdf_from_markdown

logger = logging.getLogger(__name__)


class JobBotGUI:
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("AI Job Application Tailor")
        master.geometry("1400x900")

        self.bot = JobApplicationBot()
        self.selected_resume_filepath = tk.StringVar(value="")
        self.current_job_text = ""
        self.current_job_title = "Unknown Job"

        self._setup_logging()
        self._create_widgets()

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _create_widgets(self):
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tailor_tab = tk.Frame(self.notebook)
        self.notebook.add(self.tailor_tab, text="Tailor Application")
        self._build_tailor_tab(self.tailor_tab)

        self.history_tab = tk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="History")
        self._build_history_tab(self.history_tab)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        if hasattr(ttk, 'Style'):
            ttk.Style().theme_use('clam')

    def _build_tailor_tab(self, parent_frame):
        main_frame = tk.Frame(parent_frame, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Resume Input
        top_frame = tk.Frame(main_frame)
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        resume_input_frame = tk.Frame(top_frame, padx=5, pady=5, relief=tk.GROOVE, bd=1)
        resume_input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        tk.Label(resume_input_frame, text="1. Select/Paste Your Original Resume", font=('Arial', 10, 'bold')).pack(anchor='w')

        file_control_frame = tk.Frame(resume_input_frame)
        file_control_frame.pack(fill=tk.X, pady=5)

        tk.Entry(file_control_frame, textvariable=self.selected_resume_filepath, state='readonly', width=40).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tk.Button(file_control_frame, text="Browse File", command=self._open_resume_file).pack(side=tk.LEFT)

        self.resume_text_area = scrolledtext.ScrolledText(resume_input_frame, wrap=tk.WORD, height=15)
        self.resume_text_area.pack(fill=tk.BOTH, expand=True)

        # Job Description Input
        job_input_frame = tk.Frame(top_frame, padx=5, pady=5, relief=tk.GROOVE, bd=1)
        job_input_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)

        tk.Label(job_input_frame, text="2. Paste Job Description", font=('Arial', 10, 'bold')).pack(anchor='w')

        self.job_text_area = scrolledtext.ScrolledText(job_input_frame, wrap=tk.WORD, height=15)
        self.job_text_area.pack(fill=tk.BOTH, expand=True)

        # Control & Status
        control_status_frame = tk.Frame(main_frame, pady=10)
        control_status_frame.pack(fill=tk.X)

        self.status_label = tk.Label(control_status_frame, text="Ready. Load resume and paste job details.", fg="blue", anchor='w')
        self.status_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        self.tailor_button = tk.Button(
            control_status_frame,
            text="Run AI Tailor & Save Results",
            command=self._start_tailor_thread,
            bg="#1E88E5", fg="white", font=('Arial', 12, 'bold'),
            state=tk.NORMAL
        )
        self.tailor_button.pack(side=tk.RIGHT, padx=10)

        # Output Section
        output_section_frame = tk.Frame(main_frame)
        output_section_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 5))

        output_header_frame = tk.Frame(output_section_frame)
        output_header_frame.pack(fill=tk.X)
        tk.Label(output_header_frame, text="3. Tailored Application Package", font=('Arial', 11, 'bold')).pack(side=tk.LEFT, anchor='w')

        self.export_pdf_button = tk.Button(output_header_frame, text="Export PDF", command=lambda: self._export_file("pdf"), state=tk.DISABLED)
        self.export_pdf_button.pack(side=tk.RIGHT, padx=5)

        self.export_text_button = tk.Button(output_header_frame, text="Export TXT", command=lambda: self._export_file("txt"), state=tk.DISABLED)
        self.export_text_button.pack(side=tk.RIGHT, padx=5)

        output_notebook = ttk.Notebook(output_section_frame)
        output_notebook.pack(fill=tk.BOTH, expand=True)
        self.output_notebook = output_notebook

        self.tabs = {}
        tabs_config = [("Tailored Resume (Markdown)", "resume_text"), ("Cover Letter", "cover_letter"), ("Changes Made", "changes")]
        for name, key in tabs_config:
            frame = tk.Frame(output_notebook, padx=10, pady=10)
            output_notebook.add(frame, text=name)
            text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=1, font=('Consolas', 10))
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.config(state=tk.DISABLED)
            self.tabs[key] = text_widget

    def _start_tailor_thread(self):
        resume_text = self.resume_text_area.get('1.0', tk.END).strip()
        job_text = self.job_text_area.get('1.0', tk.END).strip()

        if not resume_text or len(resume_text) < 100:
            messagebox.showwarning("Resume Required", "Please provide a complete resume (at least 100 characters).")
            return
        if not job_text or len(job_text) < 100:
            messagebox.showwarning("Job Description Required", "Please paste a complete job description.")
            return

        # UI feedback
        self.tailor_button.config(state=tk.DISABLED, text="Running AI... (10-25s)")
        self.status_label.config(text="Contacting Gemini 2.5 Flash... Please wait.", fg="orange")
        self.master.update_idletasks()

        # Run in background
        threading.Thread(target=self._run_tailor_pipeline, args=(resume_text, job_text), daemon=True).start()

    def _run_tailor_pipeline(self, resume_text: str, job_text: str):
        resume_file_name = self.selected_resume_filepath.get() or "Pasted_Resume"
        self.current_job_title = job_text.split('\n')[0].strip() or "Unknown Job"

        try:
            results = self.bot.tailor_application(resume_text, job_text, resume_file_name)
            self.master.after(0, self._update_output, results)
        except Exception as e:
            logger.exception("Tailoring failed")
            self.master.after(0, self._on_tailor_error, str(e))

    def _update_output(self, results: Dict[str, Any]):
        for key, widget in self.tabs.items():
            content = results.get(key, "No content.")
            if key == "changes" and isinstance(content, list):
                content = "\n".join(f"- {item}" for item in content)
            widget.config(state=tk.NORMAL)
            widget.delete('1.0', tk.END)
            widget.insert('1.0', content)
            widget.config(state=tk.DISABLED)

        self.export_text_button.config(state=tk.NORMAL)
        self.export_pdf_button.config(state=tk.NORMAL)
        self.status_label.config(text=f"Tailoring Complete! Saved.", fg="green")
        self.tailor_button.config(state=tk.NORMAL, text="Run AI Tailor & Save Results")

    def _on_tailor_error(self, error_msg: str):
        messagebox.showerror("Tailoring Failed", f"Error: {error_msg}")
        self.status_label.config(text="Error occurred.", fg="red")
        self.tailor_button.config(state=tk.NORMAL, text="Run AI Tailor & Save Results")

    def _export_file(self, file_type: str):
        selected_tab_id = self.output_notebook.select()
        tab_text = self.output_notebook.tab(selected_tab_id, "text")
        content_key = "resume_text" if "Resume" in tab_text else "cover_letter" if "Cover Letter" in tab_text else None

        if not content_key:
            messagebox.showinfo("Export", "Please select Resume or Cover Letter tab.")
            return

        content = self.tabs[content_key].get('1.0', tk.END).strip()
        if not content or content == "No content.":
            messagebox.showwarning("Empty", "No content to export.")
            return

        default_name = f"{'Resume' if content_key == 'resume_text' else 'Cover_Letter'}_{self.current_job_title.replace(' ', '_')}"

        try:
            if file_type == "txt":
                path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"{default_name}.txt", filetypes=[("Text", "*.txt")])
                if path:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    messagebox.showinfo("Success", f"Saved to {path}")

            elif file_type == "pdf":
                path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"{default_name}.pdf", filetypes=[("PDF", "*.pdf")])
                if path:
                    generate_pdf_from_markdown(content, path, is_cover_letter=(content_key == "cover_letter"))
                    messagebox.showinfo("Success", f"PDF saved to {path}")

        except Exception as e:
            logger.error(f"Export failed: {e}")
            messagebox.showerror("Export Failed", str(e))

    def _open_resume_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Supported", "*.txt *.md *.pdf *.docx"), ("All", "*.*")]
        )
        if filepath:
            try:
                content = extract_text_from_file(filepath)
                self.resume_text_area.delete('1.0', tk.END)
                self.resume_text_area.insert('1.0', content)
                self.selected_resume_filepath.set(os.path.basename(filepath))
                self.status_label.config(text=f"Resume loaded: {os.path.basename(filepath)}", fg="darkgreen")
            except Exception as e:
                messagebox.showerror("File Error", f"Could not read {filepath}:\n{e}")

    def _build_history_tab(self, parent_frame):
        paned_window = tk.PanedWindow(parent_frame, orient=tk.HORIZONTAL, sashwidth=5, bg="#d0d0d0")
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        list_frame = tk.Frame(paned_window, bg="white")
        paned_window.add(list_frame, minsize=300)

        tk.Label(list_frame, text="Past Applications", font=('Arial', 11, 'bold'), bg="white").pack(pady=5)

        columns = ("id", "date", "job_title")
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("job_title", text="Job Title")
        self.history_tree.column("id", width=0, stretch=tk.NO)
        self.history_tree.column("date", width=120)
        self.history_tree.column("job_title", width=250)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_select)

        details_frame = tk.Frame(paned_window, bg="#f5f5f5", padx=10, pady=10)
        paned_window.add(details_frame, minsize=500)

        tk.Label(details_frame, text="Application Details", font=('Arial', 11, 'bold'), bg="#f5f5f5").pack(anchor='w')

        self.history_notebook = ttk.Notebook(details_frame)
        self.history_notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        self.history_text_widgets = {}
        for name, key in [("Resume", "tailored_resume"), ("Cover Letter", "cover_letter"), ("Changes", "changes_made")]:
            f = tk.Frame(self.history_notebook)
            self.history_notebook.add(f, text=name)
            txt = scrolledtext.ScrolledText(f, wrap=tk.WORD, font=('Consolas', 10))
            txt.pack(fill=tk.BOTH, expand=True)
            txt.config(state=tk.DISABLED)
            self.history_text_widgets[key] = txt

        tk.Button(details_frame, text="Refresh History", command=self._load_history_list).pack(pady=5)

    def _load_history_list(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        try:
            records = self.bot.db_manager.get_history()
            for row in records:
                try:
                    dt = datetime.fromisoformat(row['timestamp'])
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = row['timestamp']
                self.history_tree.insert("",