#!/usr/bin/env python3
"""
Minimal test file to verify UI elements are created correctly
"""
import tkinter as tk
from tkinter import ttk

def test_ui_elements():
    """Test that our UI elements appear correctly"""
    print("Creating test window...")
    
    try:
        root = tk.Tk()
        root.title("UI Element Test")
        root.geometry("800x600")
        
        # Create a notebook to mimic the real app
        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create test tab
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Test Tab")
        
        # Recreate our elements exactly as in the main app
        # Job Title
        ttk.Label(tab, text="Job Title:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        job_title_entry = ttk.Entry(tab, width=50)
        job_title_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Company
        ttk.Label(tab, text="Company:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        company_entry = ttk.Entry(tab, width=50)
        company_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Job Description
        ttk.Label(tab, text="Job Description:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        job_desc_text = tk.Text(tab, width=80, height=15)
        job_desc_text.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Job URL
        ttk.Label(tab, text="Job URL:", font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=5)
        job_url_entry = ttk.Entry(tab, width=50)
        job_url_entry.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # OUR ELEMENTS - Status label (RED for visibility)
        status_label = ttk.Label(tab, text="Ready", font=('Arial', 9), foreground='red')
        status_label.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=2)
        print("Created status label")
        
        # OUR ELEMENTS - Match label (BLUE for visibility)
        match_label = ttk.Label(tab, text="Match Score: Not analyzed", font=('Arial', 10, 'bold'), foreground='blue')
        match_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=2)
        print("Created match label")
        
        # OUR ELEMENTS - Button frame with Analyze button
        button_frame = ttk.Frame(tab)
        button_frame.grid(row=6, column=0, columnspan=4, pady=10)
        
        clear_button = ttk.Button(button_frame, text="Clear Fields")
        clear_button.grid(row=0, column=0, padx=5)
        
        start_button = ttk.Button(button_frame, text="Start Tailoring")
        start_button.grid(row=0, column=1, padx=5)
        
        quit_button = ttk.Button(button_frame, text="Quit")
        quit_button.grid(row=0, column=2, padx=5)
        
        # OUR ELEMENTS - Analyze Match button
        analyze_button = ttk.Button(button_frame, text="Analyze Match")
        analyze_button.grid(row=0, column=3, padx=5)
        print("Created analyze button")
        
        print("All elements created successfully!")
        print("If you see this message but not the UI elements, there's a layout issue.")
        print("Close the window to continue...")
        
        root.mainloop()
        print("Window closed successfully")
        
    except Exception as e:
        import traceback
        print(f"Error creating test window: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_ui_elements()