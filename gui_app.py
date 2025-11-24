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
    root = tk.Tk()
    app = JobAppTkinter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
