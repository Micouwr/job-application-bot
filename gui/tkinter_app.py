"""
Tkinter GUI for the Job Application Bot.
"""

import sys
import threading
import tkinter as tk
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
        self.root.title("Job Application Bot")
        self.root.geometry("1200x800")
        self.bot = JobApplicationBot()
        self._init_ui()

    def _init_ui(self):
        """Initializes the user interface."""
        # Main container with tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Add Job & Tailor
        add_job_frame = ttk.Frame(notebook)
        notebook.add(add_job_frame, text="Add Job & Tailor")
        self._create_add_job_tab(add_job_frame)

        # Tab 2: View Jobs
        view_jobs_frame = ttk.Frame(notebook)
        notebook.add(view_jobs_frame, text="View Jobs")
        self._create_view_jobs_tab(view_jobs_frame)

        # Tab 3: Statistics
        stats_frame = ttk.Frame(notebook)
        notebook.add(stats_frame, text="Statistics")
        self._create_stats_tab(stats_frame)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_add_job_tab(self, parent):
        """Creates the 'Add Job & Tailor' tab."""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # --- Left Panel: Inputs ---
        # Job Description
        job_label = ttk.Label(left_frame, text="Job Description")
        self.job_text = tk.Text(left_frame, wrap=tk.WORD, height=15)
        job_label.pack(fill=tk.X)
        self.job_text.pack(fill=tk.BOTH, expand=True)

        # Resume
        resume_label = ttk.Label(left_frame, text="Your Resume")
        self.resume_text = tk.Text(left_frame, wrap=tk.WORD, height=15)
        resume_label.pack(fill=tk.X, pady=(10, 0))
        self.resume_text.pack(fill=tk.BOTH, expand=True)

        # Action Buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.load_button = ttk.Button(
            button_frame, text="Load Resume", command=self.load_resume
        )
        self.load_button.pack(side=tk.LEFT, padx=(0, 5))

        self.tailor_button = ttk.Button(
            button_frame, text="Tailor Application", command=self.start_tailoring
        )
        self.tailor_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(
            button_frame, text="Clear", command=self.clear_fields
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # --- Right Panel: Outputs ---
        # Tailored Resume
        tailored_resume_label = ttk.Label(right_frame, text="Tailored Resume")
        self.tailored_resume_text = tk.Text(
            right_frame, wrap=tk.WORD, state=tk.DISABLED
        )
        tailored_resume_label.pack(fill=tk.X)
        self.tailored_resume_text.pack(fill=tk.BOTH, expand=True)

        # Cover Letter
        cover_letter_label = ttk.Label(right_frame, text="Cover Letter")
        self.cover_letter_text = tk.Text(right_frame, wrap=tk.WORD, state=tk.DISABLED)
        cover_letter_label.pack(fill=tk.X, pady=(10, 0))
        self.cover_letter_text.pack(fill=tk.BOTH, expand=True)

    def _create_view_jobs_tab(self, parent):
        """Creates the 'View Jobs' tab."""
        refresh_button = ttk.Button(parent, text="Refresh", command=self.refresh_jobs)
        refresh_button.pack(pady=10)

        self.jobs_text = scrolledtext.ScrolledText(
            parent, width=100, height=30, wrap=tk.WORD
        )
        self.jobs_text.pack(padx=20, pady=10, fill="both", expand=True)

        self.refresh_jobs()

    def _create_stats_tab(self, parent):
        """Creates the 'Statistics' tab."""
        refresh_button = ttk.Button(
            parent, text="Refresh Stats", command=self.refresh_stats
        )
        refresh_button.pack(pady=10)

        self.stats_text = scrolledtext.ScrolledText(
            parent, width=100, height=30, wrap=tk.WORD
        )
        self.stats_text.pack(padx=20, pady=10, fill="both", expand=True)

        self.refresh_stats()

    def load_resume(self):
        """Loads a resume from a text file."""
        path = filedialog.askopenfilename(
            title="Open Resume",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.resume_text.delete("1.0", tk.END)
                    self.resume_text.insert(tk.END, f.read())
                self.status_var.set("Resume loaded successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load resume: {e}")

    def start_tailoring(self):
        """Starts the tailoring process in a new thread."""
        job_description = self.job_text.get("1.0", tk.END).strip()
        if not job_description:
            messagebox.showwarning("Input Required", "Please paste a job description.")
            return

        self.status_var.set("Tailoring application...")
        self.set_ui_enabled(False)

        threading.Thread(target=self.tailor_application_thread, daemon=True).start()

    def tailor_application_thread(self):
        """The actual tailoring process, run in a thread."""
        job_description = self.job_text.get("1.0", tk.END).strip()
        job = self.bot.scraper.add_manual_job(
            title="Job Application",
            company="Company",
            url="",
            description=job_description,
            location="",
        )
        match = self.bot.matcher.match_job(job)

        try:
            result = self.bot.tailor.tailor_application(job, match)
            self.root.after(0, self.on_tailoring_complete, result, None)
        except Exception as e:
            self.root.after(0, self.on_tailoring_complete, None, e)

    def on_tailoring_complete(self, result, error):
        """Handles the completion of the tailoring process."""
        self.set_ui_enabled(True)
        if error:
            messagebox.showerror("Error", f"Failed to tailor application: {error}")
            self.status_var.set("Tailoring failed.")
            return

        self.tailored_resume_text.config(state=tk.NORMAL)
        self.tailored_resume_text.delete("1.0", tk.END)
        self.tailored_resume_text.insert(tk.END, result.get("resume_text", ""))
        self.tailored_resume_text.config(state=tk.DISABLED)

        self.cover_letter_text.config(state=tk.NORMAL)
        self.cover_letter_text.delete("1.0", tk.END)
        self.cover_letter_text.insert(tk.END, result.get("cover_letter", ""))
        self.cover_letter_text.config(state=tk.DISABLED)

        self.status_var.set("Application tailored successfully.")

    def refresh_jobs(self):
        """Refresh jobs list"""
        self.jobs_text.delete("1.0", tk.END)

        try:
            with JobDatabase() as db:
                pending = db.get_pending_reviews()

            if not pending:
                self.jobs_text.insert("1.0", "No jobs pending review.")
                return

            for i, app in enumerate(pending, 1):
                self.jobs_text.insert(
                    tk.END, f"{i}. {app['title']} at {app['company']}\n"
                )
                self.jobs_text.insert(
                    tk.END, f"   Match Score: {app['match_score']*100:.1f}%\n"
                )
                self.jobs_text.insert(tk.END, f"   Location: {app['location']}\n")
                self.jobs_text.insert(tk.END, f"   URL: {app['url']}\n\n")

            self.status_var.set(f"Loaded {len(pending)} pending jobs")

        except Exception as e:
            self.jobs_text.insert("1.0", f"Error loading jobs: {e}")
            self.status_var.set(f"Error: {e}")

    def refresh_stats(self):
        """Refresh statistics"""
        self.stats_text.delete("1.0", tk.END)

        try:
            with JobDatabase() as db:
                stats = db.get_statistics()

            self.stats_text.insert("1.0", f"Total Jobs: {stats['total_jobs']}\n")
            self.stats_text.insert(
                tk.END, f"High Matches (>=80%): {stats['high_matches']}\n"
            )
            self.stats_text.insert(
                tk.END, f"Average Match Score: {stats['avg_match_score']*100:.1f}%\n\n"
            )

            self.stats_text.insert(tk.END, "Applications by Status:\n")
            for status, count in stats.get("by_status", {}).items():
                self.stats_text.insert(tk.END, f"  {status}: {count}\n")

            self.status_var.set("Statistics refreshed")

        except Exception as e:
            self.stats_text.insert("1.0", f"Error loading stats: {e}")
            self.status_var.set(f"Error: {e}")

    def clear_fields(self):
        """Clears all input and output fields."""
        self.job_text.delete("1.0", tk.END)
        self.resume_text.delete("1.0", tk.END)

        self.tailored_resume_text.config(state=tk.NORMAL)
        self.tailored_resume_text.delete("1.0", tk.END)
        self.tailored_resume_text.config(state=tk.DISABLED)

        self.cover_letter_text.config(state=tk.NORMAL)
        self.cover_letter_text.delete("1.0", tk.END)
        self.cover_letter_text.config(state=tk.DISABLED)

        self.status_var.set("Fields cleared.")

    def set_ui_enabled(self, enabled: bool):
        """Enables or disables the UI elements."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.load_button.config(state=state)
        self.tailor_button.config(state=state)
        self.clear_button.config(state=state)


def main():
    root = tk.Tk()
    app = JobAppTkinter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
