import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, ttk
import logging
import os
import numpy as np # Keep numpy import here for clean module dependencies

# Import core application logic
from .bot import JobApplicationBot
from .config import config

logger = logging.getLogger(__name__)

class JobBotGUI:
    """
    Tkinter Graphical User Interface for the Job Application Bot.
    """
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("🤖 AI Job Application Tailor")
        master.geometry("1400x900") # Increase size for more content

        # Initialize the backend bot
        self.bot = JobApplicationBot()
        self.selected_resume_filepath = tk.StringVar(value="")
        self.current_job_text = ""

        self._setup_logging()
        self._create_widgets()

    def _setup_logging(self):
        """Sets up the application logger."""
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _create_widgets(self):
        """Sets up the main layout and interactive elements."""
        
        # Use a mainframe to hold everything
        main_frame = tk.Frame(self.master, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Control and Input Section ---
        top_frame = tk.Frame(main_frame)
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        # Resume Input & File Picker (Left)
        resume_input_frame = tk.Frame(top_frame, padx=5, pady=5, relief=tk.GROOVE, bd=1)
        resume_input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(resume_input_frame, text="1. Select/Paste Your Original Resume", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        file_control_frame = tk.Frame(resume_input_frame)
        file_control_frame.pack(fill=tk.X, pady=5)
        
        tk.Entry(file_control_frame, textvariable=self.selected_resume_filepath, state='readonly', width=40).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tk.Button(file_control_frame, text="Browse File", command=self._open_resume_file).pack(side=tk.LEFT)
        
        self.resume_text_area = scrolledtext.ScrolledText(resume_input_frame, wrap=tk.WORD, height=15)
        self.resume_text_area.pack(fill=tk.BOTH, expand=True)
        
        # Job Description Input (Right)
        job_input_frame = tk.Frame(top_frame, padx=5, pady=5, relief=tk.GROOVE, bd=1)
        job_input_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(job_input_frame, text="2. Paste Job Description", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        self.job_text_area = scrolledtext.ScrolledText(job_input_frame, wrap=tk.WORD, height=15)
        self.job_text_area.pack(fill=tk.BOTH, expand=True)
        
        # --- Control & Status Section ---
        control_status_frame = tk.Frame(main_frame, pady=10)
        control_status_frame.pack(fill=tk.X)

        # Status Bar
        self.status_label = tk.Label(control_status_frame, text="Ready. Load resume and paste job details.", fg="blue", anchor='w')
        self.status_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Tailor Button
        tailor_button = tk.Button(control_status_frame, text="🚀 Run AI Tailor & Save Results", command=self._run_tailor_pipeline, bg="#1E88E5", fg="white", font=('Arial', 12, 'bold'))
        tailor_button.pack(side=tk.RIGHT, padx=10)

        # --- Output Section (Bottom) ---
        tk.Label(main_frame, text="3. Tailored Application Package", font=('Arial', 11, 'bold')).pack(pady=(10, 5), anchor='w')
        
        output_notebook = ttk.Notebook(main_frame)
        output_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create output tabs
        self.tabs = {}
        tabs_config = [
            ("Tailored Resume (Markdown)", "resume_text"),
            ("Cover Letter", "cover_letter"),
            ("Changes Made (for Review)", "changes")
        ]
        
        for name, key in tabs_config:
            frame = tk.Frame(output_notebook, padx=10, pady=10)
            output_notebook.add(frame, text=name)
            
            # Use a slightly larger font for readability
            text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=1, font=('Consolas', 10))
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.config(state=tk.DISABLED) # Make read-only
            self.tabs[key] = text_widget
        
        # Initialize Ttk style
        ttk.Style().theme_use('clam')

    def _open_resume_file(self):
        """Opens a file dialog, reads the selected file, and populates the text area."""
        filepath = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.resume_text_area.delete('1.0', tk.END)
                self.resume_text_area.insert('1.0', content)
                
                # Store only the filename for logging purposes
                filename = os.path.basename(filepath)
                self.selected_resume_filepath.set(filename)
                self.status_label.config(text=f"Resume loaded: {filename}", fg="darkgreen")
                
            except Exception as e:
                messagebox.showerror("File Error", f"Could not read file {filepath}:\n{e}")
                logger.error("File reading error: %s", e)

    def _update_output(self, results: Dict[str, Any]):
        """Updates the output text areas with the results."""
        for key, widget in self.tabs.items():
            content = results.get(key, "No content generated.")
            
            # Special formatting for the list of changes
            if key == "changes" and isinstance(content, list):
                content = "\n".join(f"- {item}" for item in content)
            
            widget.config(state=tk.NORMAL)
            widget.delete('1.0', tk.END)
            widget.insert('1.0', content)
            widget.config(state=tk.DISABLED)
            
        self.status_label.config(text=f"Tailoring Complete! Results saved to {self.bot.db_manager.DB_NAME}.", fg="green")

    def _run_tailor_pipeline(self):
        """
        Gathers input and runs the full AI tailoring process.
        """
        resume_text = self.resume_text_area.get('1.0', tk.END).strip()
        job_text = self.job_text_area.get('1.0', tk.END).strip()
        resume_file_name = self.selected_resume_filepath.get() or "Pasted_Content_Resume"

        if not resume_text or not job_text:
            messagebox.showerror("Input Error", "Please provide content for both the Resume and the Job Description.")
            return

        self.status_label.config(text="Running AI Tailor... 🤖 Contacting Gemini API. Please wait.", fg="orange")
        self.master.update_idletasks() # Force GUI update

        try:
            # The core bot logic handles the AI call and the database logging
            results = self.bot.tailor_application(
                resume_text=resume_text, 
                job_text=job_text,
                resume_file_name=resume_file_name
            )
            
            self._update_output(results)

        except ValueError as e:
            # Handle malformed response from AI
            self.status_label.config(text="Error occurred.", fg="red")
            messagebox.showerror("Parsing Error", f"The AI response was malformed or missing required tags:\n{e}")
            logger.error("Parsing error: %s", e)
        except RuntimeError as e:
            # Handle API call failures (e.g., key missing, network error, 4xx/5xx)
            self.status_label.config(text="API Error occurred.", fg="red")
            messagebox.showerror("API Error", f"A critical API error occurred:\n{e}\n\nPlease check your GEMINI_API_KEY and network connection.")
            logger.error("Runtime error: %s", e)
        except Exception as e:
            # Catch all other exceptions
            self.status_label.config(text="Application Error.", fg="red")
            messagebox.showerror("Application Error", f"An unexpected error occurred:\n{e}")
            logger.error("Unexpected error: %s", e)


def start_gui():
    """Initializes and runs the Tkinter application."""
    root = tk.Tk()
    JobBotGUI(root)
    root.mainloop()

if __name__ == '__main__':
    start_gui()