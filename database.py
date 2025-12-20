import sqlite3
import json
from pathlib import Path
from datetime import datetime
from config.settings import DB_PATH, OUTPUT_PATH

class DatabaseManager:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_title TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    job_url TEXT,
                    resume_path TEXT,
                    cover_letter_path TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS resumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    file_path TEXT NOT NULL UNIQUE,
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def add_application(self, job_title, company_name, job_url, resume_path, cover_letter_path, job_description_path=None):
        """Add a new job application"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO applications (job_title, company_name, job_url, resume_path, cover_letter_path, job_description_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (job_title, company_name, job_url, resume_path, cover_letter_path, job_description_path))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_all_applications(self):
        """Get all job applications"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM applications ORDER BY created_at DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_application_status(self, app_id, status):
        """Update application status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE applications 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, app_id))
            
            conn.commit()
    
    def delete_application(self, app_id):
        """Delete an application"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM applications WHERE id = ?', (app_id,))
            conn.commit()
