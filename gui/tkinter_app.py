"""
Tkinter GUI for the Job Application Bot.
"""

import sys
from pathlib import Path

# Add project root to path to allow direct execution
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

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
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top frame for actions
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        search_button = ttk.Button(
            top_frame, text="Search", command=self.refresh_jobs_table
        )
        search_button.pack(side=tk.LEFT, padx=5)

        refresh_button = ttk.Button(
            top_frame, text="Refresh", command=self.refresh_jobs_table
        )
        refresh_button.pack(side=tk.RIGHT)

        # Paned window for resizing
        paned_window = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # Top pane: Treeview for jobs list
        tree_frame = ttk.Frame(paned_window)
        paned_window.add(tree_frame, weight=2)

        columns = ("id", "title", "company", "score", "status")
        self.jobs_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            displaycolumns=("title", "company", "score", "status"),
        )

        self.jobs_tree.heading("title", text="Job Title")
        self.jobs_tree.heading("company", text="Company")
        self.jobs_tree.heading("score", text="Match Score")
        self.jobs_tree.heading("status", text="Status")

        self.jobs_tree.column("title", width=400, anchor=tk.W)
        self.jobs_tree.column("company", width=200, anchor=tk.W)
        self.jobs_tree.column("score", width=100, anchor=tk.CENTER)
        self.jobs_tree.column("status", width=150, anchor=tk.CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            tree_frame, orient=tk.VERTICAL, command=self.jobs_tree.yview
        )
        self.jobs_tree.configure(yscroll=scrollbar.set)

        self.jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom pane: Details and actions
        bottom_frame = ttk.Frame(paned_window)
        paned_window.add(bottom_frame, weight=1)

        # Details view
        details_frame = ttk.Notebook(bottom_frame)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.job_desc_text = self._create_text_tab(details_frame, "Job Description")
        self.tailored_resume_details_text = self._create_text_tab(
            details_frame, "Tailored Resume"
        )
        self.cover_letter_details_text = self._create_text_tab(
            details_frame, "Cover Letter"
        )

        # Status update buttons
        status_frame = ttk.LabelFrame(bottom_frame, text="Update Status", padding="10")
        status_frame.pack(fill=tk.X)

        statuses = [
            "Pending Review",
            "Applied",
            "Interview Scheduled",
            "Offer Received",
            "Rejected",
            "Archived",
        ]
        for status in statuses:
            btn = ttk.Button(
                status_frame,
                text=status,
                command=lambda s=status: self.update_job_status(s),
            )
            btn.pack(side=tk.LEFT, padx=5)

        # Bind selection event
        self.jobs_tree.bind("<<TreeviewSelect>>", self.on_job_select)

        self.refresh_jobs_table()

    def _create_text_tab(self, notebook, title):
        """Creates a scrolled text widget in a new tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)
        return text_widget

    def on_job_select(self, event):
        """Handles the job selection event."""
        selected_item = self.jobs_tree.focus()
        if not selected_item:
            return

        job_id = self.jobs_tree.item(selected_item)["values"][0]

        with JobDatabase() as db:
            details = db.get_application_details(job_id)

        if not details:
            return

        # Enable text widgets for update
        self.job_desc_text.config(state=tk.NORMAL)
        self.tailored_resume_details_text.config(state=tk.NORMAL)
        self.cover_letter_details_text.config(state=tk.NORMAL)

        # Clear and insert new content
        self.job_desc_text.delete("1.0", tk.END)
        self.job_desc_text.insert(tk.END, details.get("description", "Not available."))

        self.tailored_resume_details_text.delete("1.0", tk.END)
        self.tailored_resume_details_text.insert(
            tk.END, details.get("tailored_resume", "Not available.")
        )

        self.cover_letter_details_text.delete("1.0", tk.END)
        self.cover_letter_details_text.insert(
            tk.END, details.get("cover_letter", "Not available.")
        )

        # Disable text widgets to make them read-only
        self.job_desc_text.config(state=tk.DISABLED)
        self.tailored_resume_details_text.config(state=tk.DISABLED)
        self.cover_letter_details_text.config(state=tk.DISABLED)

    def update_job_status(self, new_status: str):
        """Updates the status of the selected job."""
        selected_item = self.jobs_tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a job to update.")
            return

        job_id = self.jobs_tree.item(selected_item)["values"][0]

        with JobDatabase() as db:
            db.update_status(job_id, new_status.lower().replace(" ", "_"))

        self.refresh_jobs_table()
        self.status_var.set(f"Status updated to '{new_status}'")

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

    def refresh_jobs_table(self):
        """Refresh jobs list"""
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)

        try:
            search_term = self.search_var.get()
            with JobDatabase() as db:
                all_jobs = db.get_all_jobs(search_term)

            if not all_jobs:
                return

            for job in all_jobs:
                score = (
                    f"{job['match_score']*100:.1f}%" if job["match_score"] else "N/A"
                )
                status = job.get("application_status", "Not Processed")
                self.jobs_tree.insert(
                    "",
                    tk.END,
                    values=(job["id"], job["title"], job["company"], score, status),
                )

            self.status_var.set(f"Loaded {len(all_jobs)} jobs")

        except Exception as e:
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
    JobAppTkinter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
