#!/usr/bin/env python3
"""
Job Application Bot - Desktop GUI
No terminal needed - just double-click to run!
"""

import tkinter as tk

from gui.tkinter_app import JobAppTkinter


def main():
    """
    Launches the Tkinter GUI for the Job Application Bot.
    """
    try:
        # Import core components here to catch initialization errors
        from database import JobDatabase
        from main import JobApplicationBot

        # Initialize backend components
        db = JobDatabase()
        bot = JobApplicationBot()

        # Initialize and run the GUI
        root = tk.Tk()
        app = JobAppTkinter(root, bot, db)
        root.mainloop()
    except Exception as e:
        # Provide a fallback error message if the GUI can't start
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw() # Hide the main window
        messagebox.showerror(
            "Fatal Error",
            f"A critical error occurred and the application cannot start:\n\n{e}\n\n"
            "Please check your .env file and ensure all dependencies are installed."
        )
        root.destroy()


if __name__ == "__main__":
    main()
