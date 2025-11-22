#!/usr/bin/env python3
"""
Job Application Bot - Desktop GUI
No terminal needed - just double-click to run!
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from main import JobApplicationBot
from database import JobDatabase


class JobBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Job Application Bot")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize bot
        try:
            self.bot = JobApplicationBot()
            self.status_var = tk.StringVar(value="✓ Bot initialized successfully!")
        except Exception as e:
            self.status_var = tk.StringVar(value=f"❌ Error: {e}")
            self.bot = None
        
        self.create_widgets()
    
    def create_widgets(self):
        # Title Frame
        title_frame = tk.Frame(self.root, bg='#667eea', height=80)
        title_frame.pack(fill='x', pady=0)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="🤖 Job Application Bot", 
            font=('Arial', 24, 'bold'),
            bg='#667eea',
            fg='white'
        )
        title_label.pack(pady=20)
        
        # Main container with tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Add Job
        add_job_frame = tk.Frame(notebook, bg='white')
        notebook.add(add_job_frame, text='📝 Add Job')
        self.create_add_job_tab(add_job_frame)
        
        # Tab 2: View Jobs
        view_jobs_frame = tk.Frame(notebook, bg='white')
        notebook.add(view_jobs_frame, text='📋 View Jobs')
        self.create_view_jobs_tab(view_jobs_frame)
        
        # Tab 3: Statistics
        stats_frame = tk.Frame(notebook, bg='white')
        notebook.add(stats_frame, text='📊 Statistics')
        self.create_stats_tab(stats_frame)
        
        # Status bar
        status_frame = tk.Frame(self.root, bg='#f0f0f0', height=30)
        status_frame.pack(fill='x', side='bottom')
        
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg='#f0f0f0',
            fg='#333',
            font=('Arial', 10)
        )
        status_label.pack(side='left', padx=10, pady=5)
    
    def create_add_job_tab(self, parent):
        # Scrollable frame
        canvas = tk.Canvas(parent, bg='white')
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Title field
        tk.Label(
            scrollable_frame, 
            text="Job Title: *", 
            font=('Arial', 12, 'bold'),
            bg='white'
        ).grid(row=0, column=0, sticky='w', padx=20, pady=(20, 5))
        
        self.title_entry = tk.Entry(scrollable_frame, width=60, font=('Arial', 11))
        self.title_entry.grid(row=1, column=0, padx=20, pady=(0, 15), sticky='ew')
        
        # Company field (optional)
        tk.Label(
            scrollable_frame, 
            text="Company: (optional)", 
            font=('Arial', 12, 'bold'),
            bg='white'
        ).grid(row=2, column=0, sticky='w', padx=20, pady=(0, 5))
        
        self.company_entry = tk.Entry(scrollable_frame, width=60, font=('Arial', 11))
        self.company_entry.grid(row=3, column=0, padx=20, pady=(0, 15), sticky='ew')
        
        # URL field (optional)
        tk.Label(
            scrollable_frame, 
            text="Job URL: (optional)", 
            font=('Arial', 12, 'bold'),
            bg='white'
        ).grid(row=4, column=0, sticky='w', padx=20, pady=(0, 5))
        
        self.url_entry = tk.Entry(scrollable_frame, width=60, font=('Arial', 11))
        self.url_entry.grid(row=5, column=0, padx=20, pady=(0, 15), sticky='ew')
        
        # Location field
        tk.Label(
            scrollable_frame, 
            text="Location:", 
            font=('Arial', 12, 'bold'),
            bg='white'
        ).grid(row=6, column=0, sticky='w', padx=20, pady=(0, 5))
        
        self.location_entry = tk.Entry(scrollable_frame, width=60, font=('Arial', 11))
        self.location_entry.insert(0, "Louisville, KY")
        self.location_entry.grid(row=7, column=0, padx=20, pady=(0, 15), sticky='ew')
        
        # Description field
        tk.Label(
            scrollable_frame, 
            text="Job Description:", 
            font=('Arial', 12, 'bold'),
            bg='white'
        ).grid(row=8, column=0, sticky='w', padx=20, pady=(0, 5))
        
        self.description_text = scrolledtext.ScrolledText(
            scrollable_frame, 
            width=60, 
            height=12,
            font=('Arial', 10),
            wrap=tk.WORD
        )
        self.description_text.grid(row=9, column=0, padx=20, pady=(0, 15), sticky='ew')
        
        # Buttons frame
        button_frame = tk.Frame(scrollable_frame, bg='white')
        button_frame.grid(row=10, column=0, padx=20, pady=20)
        
        # Add & Process button
        add_button = tk.Button(
            button_frame,
            text="🚀 Add Job & Process",
            font=('Arial', 12, 'bold'),
            bg='#667eea',
            fg='white',
            padx=30,
            pady=10,
            cursor='hand2',
            command=self.add_job
        )
        add_button.pack(side='left', padx=5)
        
        # Clear button
        clear_button = tk.Button(
            button_frame,
            text="🗑️ Clear Form",
            font=('Arial', 12),
            bg='#f44336',
            fg='white',
            padx=30,
            pady=10,
            cursor='hand2',
            command=self.clear_form
        )
        clear_button.pack(side='left', padx=5)
        
        # Configure grid
        scrollable_frame.columnconfigure(0, weight=1)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_view_jobs_tab(self, parent):
        # Refresh button
        refresh_button = tk.Button(
            parent,
            text="🔄 Refresh",
            font=('Arial', 11),
            bg='#667eea',
            fg='white',
            padx=20,
            pady=5,
            cursor='hand2',
            command=self.refresh_jobs
        )
        refresh_button.pack(pady=10)
        
        # Jobs list
        self.jobs_text = scrolledtext.ScrolledText(
            parent,
            width=100,
            height=30,
            font=('Courier', 10),
            wrap=tk.WORD
        )
        self.jobs_text.pack(padx=20, pady=10, fill='both', expand=True)
        
        # Load jobs
        self.refresh_jobs()
    
    def create_stats_tab(self, parent):
        # Refresh button
        refresh_button = tk.Button(
            parent,
            text="🔄 Refresh Stats",
            font=('Arial', 11),
            bg='#667eea',
            fg='white',
            padx=20,
            pady=5,
            cursor='hand2',
            command=self.refresh_stats
        )
        refresh_button.pack(pady=10)
        
        # Stats display
        self.stats_text = scrolledtext.ScrolledText(
            parent,
            width=100,
            height=30,
            font=('Arial', 12),
            wrap=tk.WORD
        )
        self.stats_text.pack(padx=20, pady=10, fill='both', expand=True)
        
        # Load stats
        self.refresh_stats()
    
    def add_job(self):
        """Add job and process it"""
        if not self.bot:
            messagebox.showerror("Error", "Bot not initialized. Check your .env file!")
            return
        
        title = self.title_entry.get().strip()
        company = self.company_entry.get().strip() or None
        url = self.url_entry.get().strip() or None
        location = self.location_entry.get().strip()
        description = self.description_text.get("1.0", tk.END).strip()
        
        if not title:
            messagebox.showwarning("Missing Info", "Job title is required!")
            return
        
        # Show processing message
        self.status_var.set("⏳ Processing job... Please wait...")
        self.root.update()
        
        # Run in thread to avoid freezing GUI
        def process():
            try:
                # Add job
                job = self.bot.add_manual_job(
                    title=title,
                    company=company,
                    url=url,
                    description=description,
                    location=location
                )
                
                # Process it
                self.bot.run_pipeline(manual_jobs=[job])
                
                # Success
                self.root.after(0, lambda: self.status_var.set(
                    f"✓ Job '{title}' added and processed successfully!"
                ))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success!", 
                    f"Job added: {title}\n\nCheck 'View Jobs' tab to see results!"
                ))
                self.root.after(0, self.clear_form)
                self.root.after(0, self.refresh_jobs)
                self.root.after(0, self.refresh_stats)
                
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"❌ Error: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        thread = threading.Thread(target=process, daemon=True)
        thread.start()
    
    def clear_form(self):
        """Clear all form fields"""
        self.title_entry.delete(0, tk.END)
        self.company_entry.delete(0, tk.END)
        self.url_entry.delete(0, tk.END)
        self.location_entry.delete(0, tk.END)
        self.location_entry.insert(0, "Louisville, KY")
        self.description_text.delete("1.0", tk.END)
        self.status_var.set("Form cleared")
    
    def refresh_jobs(self):
        """Refresh jobs list"""
        self.jobs_text.delete("1.0", tk.END)
        
        try:
            with JobDatabase() as db:
                pending = db.get_pending_reviews()
            
            if not pending:
                self.jobs_text.insert("1.0", "No jobs pending review.\n\nAdd a job in the 'Add Job' tab!")
                return
            
            self.jobs_text.insert("1.0", f"{'='*80}\n")
            self.jobs_text.insert(tk.END, f"PENDING REVIEW ({len(pending)} applications)\n")
            self.jobs_text.insert(tk.END, f"{'='*80}\n\n")
            
            for i, app in enumerate(pending, 1):
                self.jobs_text.insert(tk.END, f"{i}. {app['title']} at {app['company']}\n")
                self.jobs_text.insert(tk.END, f"   Match Score: {app['match_score']*100:.1f}%\n")
                self.jobs_text.insert(tk.END, f"   Location: {app['location']}\n")
                self.jobs_text.insert(tk.END, f"   URL: {app['url']}\n")
                self.jobs_text.insert(tk.END, f"\n")
            
            self.status_var.set(f"✓ Loaded {len(pending)} pending jobs")
            
        except Exception as e:
            self.jobs_text.insert("1.0", f"Error loading jobs: {e}")
            self.status_var.set(f"❌ Error: {e}")
    
    def refresh_stats(self):
        """Refresh statistics"""
        self.stats_text.delete("1.0", tk.END)
        
        try:
            with JobDatabase() as db:
                stats = db.get_statistics()
            
            self.stats_text.insert("1.0", f"{'='*80}\n")
            self.stats_text.insert(tk.END, f"📊 JOB APPLICATION STATISTICS\n")
            self.stats_text.insert(tk.END, f"{'='*80}\n\n")
            
            self.stats_text.insert(tk.END, f"Total Jobs: {stats['total_jobs']}\n\n")
            self.stats_text.insert(tk.END, f"High Matches (≥80%): {stats['high_matches']}\n\n")
            self.stats_text.insert(tk.END, f"Average Match Score: {stats['avg_match_score']*100:.1f}%\n\n")
            
            self.stats_text.insert(tk.END, f"\nApplications by Status:\n")
            self.stats_text.insert(tk.END, f"{'-'*40}\n")
            
            for status, count in stats.get('by_status', {}).items():
                self.stats_text.insert(tk.END, f"  {status}: {count}\n")
            
            if not stats.get('by_status'):
                self.stats_text.insert(tk.END, "  No applications yet\n")
            
            self.stats_text.insert(tk.END, f"\n{'='*80}\n")
            self.stats_text.insert(tk.END, f"\nNext Steps:\n")
            self.stats_text.insert(tk.END, f"1. Add more jobs in 'Add Job' tab\n")
            self.stats_text.insert(tk.END, f"2. Review applications in 'View Jobs' tab\n")
            self.stats_text.insert(tk.END, f"3. Check output/ folder for tailored resumes\n")
            
            self.status_var.set("✓ Statistics refreshed")
            
        except Exception as e:
            self.stats_text.insert("1.0", f"Error loading stats: {e}")
            self.status_var.set(f"❌ Error: {e}")


def main():
    root = tk.Tk()
    app = JobBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
