import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, ttk
import logging
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
    # Fallback for direct execution
    from bot import JobApplicationBot
    from config import config
    from utils import extract_text_from_file, generate_pdf_from_markdown

logger = logging.getLogger(__name__)

class JobBotGUI:
    """
    Tkinter Graphical User Interface for the Job Application Bot.
    """
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("🤖 AI Job Application Tailor")
        master.geometry("1400x900")

        # Initialize the backend bot
        self.bot = JobApplicationBot()
        self.selected_resume_filepath = tk.StringVar(value="")
        self.current_job_text = ""
        self.current_job_title = "Unknown Job" # Added to use in export file names

        self._setup_logging()
        self._create_widgets()

    def _setup_logging(self):
        """Sets up the application logger."""
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _create_widgets(self):
        """Sets up the main layout and interactive elements."""
        
        # Main Layout Container (Tabbed Interface)
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- TAB 1: Tailor Application (The existing main interface) ---
        self.tailor_tab = tk.Frame(self.notebook)
        self.notebook.add(self.tailor_tab, text="✨ Tailor Application")
        self._build_tailor_tab(self.tailor_tab)

        # --- TAB 2: History Viewer ---
        self.history_tab = tk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="📜 History")
        self._build_history_tab(self.history_tab)
        
        # Bind tab change event to refresh history
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # Initialize Ttk style
        if hasattr(ttk, 'Style'):
            ttk.Style().theme_use('clam')

    def _build_tailor_tab(self, parent_frame):
        """Constructs the original tailoring interface inside the given frame."""
        main_frame = tk.Frame(parent_frame, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ... (Resume Input & File Picker) ...
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
        
        # ... (Job Description Input) ...
        job_input_frame = tk.Frame(top_frame, padx=5, pady=5, relief=tk.GROOVE, bd=1)
        job_input_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(job_input_frame, text="2. Paste Job Description", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        self.job_text_area = scrolledtext.ScrolledText(job_input_frame, wrap=tk.WORD, height=15)
        self.job_text_area.pack(fill=tk.BOTH, expand=True)
        
        # ... (Control & Status) ...
        control_status_frame = tk.Frame(main_frame, pady=10)
        control_status_frame.pack(fill=tk.X)

        self.status_label = tk.Label(control_status_frame, text="Ready. Load resume and paste job details.", fg="blue", anchor='w')
        self.status_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        tailor_button = tk.Button(control_status_frame, text="🚀 Run AI Tailor & Save Results", command=self._run_tailor_pipeline, bg="#1E88E5", fg="white", font=('Arial', 12, 'bold'))
        tailor_button.pack(side=tk.RIGHT, padx=10)

        # ... (Output Section) ...
        output_section_frame = tk.Frame(main_frame)
        output_section_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 5))

        output_header_frame = tk.Frame(output_section_frame)
        output_header_frame.pack(fill=tk.X)
        tk.Label(output_header_frame, text="3. Tailored Application Package", font=('Arial', 11, 'bold')).pack(side=tk.LEFT, anchor='w')
        
        # --- NEW: Export Buttons ---
        self.export_pdf_button = tk.Button(output_header_frame, text="📄 Export PDF", command=lambda: self._export_file(file_type="pdf"), state=tk.DISABLED)
        self.export_pdf_button.pack(side=tk.RIGHT, padx=5)

        self.export_text_button = tk.Button(output_header_frame, text="📝 Export TXT", command=lambda: self._export_file(file_type="txt"), state=tk.DISABLED)
        self.export_text_button.pack(side=tk.RIGHT, padx=5)
        
        # Output Notebook
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

    # ... (Rest of the GUI methods: _build_history_tab, _load_history_list, etc., remain the same) ...
    # Removed the redundant code block for brevity, assuming the user will overwrite the full file.

    # --- NEW: Export Functionality ---

    def _export_file(self, file_type: str):
        """Exports the content of the currently active output tab."""
        
        # 1. Determine which tab is active
        selected_tab_id = self.output_notebook.select()
        tab_text = self.output_notebook.tab(selected_tab_id, "text")
        
        content_key = None
        if "Resume" in tab_text:
            content_key = "resume_text"
            default_name = f"Tailored_Resume_{self.current_job_title.replace(' ', '_')}"
        elif "Cover Letter" in tab_text:
            content_key = "cover_letter"
            default_name = f"Cover_Letter_{self.current_job_title.replace(' ', '_')}"
        else:
            messagebox.showinfo("Export Info", "Please select either the Resume or Cover Letter tab to export.")
            return

        # 2. Get content from the selected tab
        content_widget = self.tabs[content_key]
        content = content_widget.get('1.0', tk.END).strip()
        
        if not content:
            messagebox.showwarning("Export Warning", "The selected tab is empty. Run the AI tailor first.")
            return

        try:
            # 3. Handle TXT Export
            if file_type == "txt":
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    initialfile=f"{default_name}.txt",
                    filetypes=[("Text files", "*.txt")]
                )
                if filepath:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    messagebox.showinfo("Export Success", f"Content successfully saved to:\n{filepath}")

            # 4. Handle PDF Export
            elif file_type == "pdf":
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    initialfile=f"{default_name}.pdf",
                    filetypes=[("PDF files", "*.pdf")]
                )
                if filepath:
                    is_cover_letter = "Cover Letter" in tab_text
                    generate_pdf_from_markdown(content, filepath, is_cover_letter=is_cover_letter)
                    messagebox.showinfo("Export Success", f"PDF successfully generated and saved to:\n{filepath}")

        except Exception as e:
            logger.error(f"Export failed: {e}")
            messagebox.showerror("Export Error", f"Failed to export file: {e}")

    def _update_output(self, results: Dict[str, Any]):
        # ... (Existing update logic) ...
        for key, widget in self.tabs.items():
            content = results.get(key, "No content.")
            if key == "changes" and isinstance(content, list): content = "\n".join(f"- {item}" for item in content)
            widget.config(state=tk.NORMAL)
            widget.delete('1.0', tk.END)
            widget.insert('1.0', content)
            widget.config(state=tk.DISABLED)
        
        # Enable Export buttons after successful tailoring
        self.export_text_button.config(state=tk.NORMAL)
        self.export_pdf_button.config(state=tk.NORMAL)

        self.status_label.config(text=f"Tailoring Complete! Saved to {self.bot.db_manager.DB_NAME}.", fg="green")

    def _run_tailor_pipeline(self):
        resume_text = self.resume_text_area.get('1.0', tk.END).strip()
        job_text = self.job_text_area.get('1.0', tk.END).strip()
        resume_file_name = self.selected_resume_filepath.get() or "Pasted_Content_Resume"

        # Simple extraction of a job title for file naming
        lines = job_text.split('\n')
        self.current_job_title = lines[0].strip() if lines and lines[0].strip() else "Unknown Job"

        if not resume_text or not job_text:
            messagebox.showerror("Input Error", "Please provide content for both the Resume and the Job Description.")
            return

        self.status_label.config(text="Running AI Tailor... 🤖 Contacting Gemini API. Please wait.", fg="orange")
        self.master.update_idletasks()

        # Disable Export buttons while running
        self.export_text_button.config(state=tk.DISABLED)
        self.export_pdf_button.config(state=tk.DISABLED)

        try:
            results = self.bot.tailor_application(resume_text, job_text, resume_file_name)
            self._update_output(results)
        except Exception as e:
            self.status_label.config(text="Error occurred.", fg="red")
            messagebox.showerror("Error", str(e))
            logger.error(e)

    # --- Retaining other helper methods for completeness ---

    def _open_resume_file(self):
        """
        Updated to support PDF and DOCX using the new utils module.
        """
        filepath = filedialog.askopenfilename(
            defaultextension=".txt",
            # Allow all supported types
            filetypes=[
                ("Supported Files", "*.txt *.md *.pdf *.docx"),
                ("Text files", "*.txt"),
                ("PDF files", "*.pdf"),
                ("Word files", "*.docx"),
                ("All files", "*.*")
            ]
        )
        if filepath:
            try:
                # Use the new utility to extract text
                content = extract_text_from_file(filepath)
                
                self.resume_text_area.delete('1.0', tk.END)
                self.resume_text_area.insert('1.0', content)
                
                filename = os.path.basename(filepath)
                self.selected_resume_filepath.set(filename)
                self.status_label.config(text=f"Resume loaded: {filename}", fg="darkgreen")
                
            except Exception as e:
                messagebox.showerror("File Error", f"Could not read file {filepath}:\n{e}")
                logger.error("File reading error: %s", e)

    def _build_history_tab(self, parent_frame):
        """Constructs the History Viewer tab."""
        # Split into Left (List) and Right (Details)
        paned_window = tk.PanedWindow(parent_frame, orient=tk.HORIZONTAL, sashwidth=5, bg="#d0d0d0")
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Left: History List ---
        list_frame = tk.Frame(paned_window, bg="white")
        paned_window.add(list_frame, minsize=300)

        tk.Label(list_frame, text="Past Applications", font=('Arial', 11, 'bold'), bg="white").pack(pady=5)
        
        # Treeview for columns (Date, Job Title)
        columns = ("id", "date", "job_title")
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("job_title", text="Job Title")
        self.history_tree.column("id", width=0, stretch=tk.NO) # Hidden ID column
        self.history_tree.column("date", width=120)
        self.history_tree.column("job_title", width=250)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_select)

        # --- Right: Details View ---
        details_frame = tk.Frame(paned_window, bg="#f5f5f5", padx=10, pady=10)
        paned_window.add(details_frame, minsize=500)

        tk.Label(details_frame, text="Application Details", font=('Arial', 11, 'bold'), bg="#f5f5f5").pack(anchor='w')

        # Details Output Notebook (Resume vs Cover Letter)
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

        # Refresh Button
        refresh_btn = tk.Button(details_frame, text="🔄 Refresh History", command=self._load_history_list)
        refresh_btn.pack(pady=5)

    def _load_history_list(self):
        """Fetches history from the database and populates the Treeview."""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        try:
            records = self.bot.db_manager.get_history()
            
            for row in records:
                try:
                    dt = datetime.fromisoformat(row['timestamp'])
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    date_str = row['timestamp']

                self.history_tree.insert("", "end", iid=row['id'], values=(row['id'], date_str, row['job_title']))
                
        except Exception as e:
            logger.error("Failed to load history list: %s", e)

    def _on_history_select(self, event):
        """Handles selection from the history list."""
        selected_items = self.history_tree.selection()
        if not selected_items:
            return

        history_id = selected_items[0]
        
        try:
            conn = sqlite3.connect(self.bot.db_manager.DB_NAME)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tailoring_results WHERE history_id = ?", (history_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                self._display_history_detail(dict(result))
            else:
                self._display_history_detail({"tailored_resume": "No details found.", "cover_letter": "", "changes_made": ""})

        except Exception as e:
            logger.error("Error fetching history details: %s", e)
            messagebox.showerror("Database Error", f"Could not load details: {e}")

    def _display_history_detail(self, data: Dict[str, Any]):
        """Updates the right-hand details pane."""
        for key, widget in self.history_text_widgets.items():
            content = data.get(key, "")
            widget.config(state=tk.NORMAL)
            widget.delete('1.0', tk.END)
            widget.insert('1.0', content)
            widget.config(state=tk.DISABLED)

    def _on_tab_change(self, event):
        """Event handler for tab switching."""
        selected_tab = event.widget.select()
        tab_text = event.widget.tab(selected_tab, "text")
        
        if tab_text == "📜 History":
            self._load_history_list()
        
def start_gui():
    root = tk.Tk()
    JobBotGUI(root)
    root.mainloop()

if __name__ == '__main__':
    start_gui()