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
            # Check if applications table exists and has match_score column
            cursor = conn.execute("PRAGMA table_info(applications)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'match_score' not in columns:
                # Need to add match_score column
                if columns:
                    # Table exists but without match_score, need to recreate
                    conn.execute('''
                        CREATE TABLE applications_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            job_title TEXT NOT NULL,
                            company_name TEXT NOT NULL,
                            job_url TEXT,
                            resume_path TEXT,
                            cover_letter_path TEXT,
                            job_description_path TEXT,
                            match_score INTEGER DEFAULT 0,
                            match_summary TEXT,
                            status TEXT DEFAULT 'pending',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    # Copy existing data
                    if 'status' in columns:
                        conn.execute('''
                            INSERT INTO applications_new 
                            (id, job_title, company_name, job_url, resume_path, cover_letter_path, job_description_path, status, created_at, updated_at)
                            SELECT id, job_title, company_name, job_url, resume_path, cover_letter_path, job_description_path, status, created_at, updated_at 
                            FROM applications
                        ''')
                    else:
                        conn.execute('''
                            INSERT INTO applications_new 
                            (id, job_title, company_name, job_url, resume_path, cover_letter_path, job_description_path, created_at, updated_at)
                            SELECT id, job_title, company_name, job_url, resume_path, cover_letter_path, job_description_path, created_at, updated_at 
                            FROM applications
                        ''')
                    
                    # Drop old table and rename new one
                    conn.execute('DROP TABLE applications')
                    conn.execute('ALTER TABLE applications_new RENAME TO applications')
                else:
                    # Fresh table creation
                    conn.execute('''
                        CREATE TABLE applications (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            job_title TEXT NOT NULL,
                            company_name TEXT NOT NULL,
                            job_url TEXT,
                            resume_path TEXT,
                            cover_letter_path TEXT,
                            job_description_path TEXT,
                            match_score INTEGER DEFAULT 0,
                            match_summary TEXT,
                            status TEXT DEFAULT 'pending',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
            else:
                # Table already has match_score column, check if match_summary exists
                if 'match_summary' not in columns:
                    # Add match_summary column if it doesn't exist
                    conn.execute('ALTER TABLE applications ADD COLUMN match_summary TEXT')
                
                # Ensure the table exists (no-op if it already exists)
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS applications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_title TEXT NOT NULL,
                        company_name TEXT NOT NULL,
                        job_url TEXT,
                        resume_path TEXT,
                        cover_letter_path TEXT,
                        job_description_path TEXT,
                        match_score INTEGER DEFAULT 0,
                        match_summary TEXT,
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
    
    def add_application(self, job_title, company_name, job_url, resume_path, cover_letter_path, job_description_path=None, match_score=0, match_summary=None):
        """Add a new job application"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO applications (job_title, company_name, job_url, resume_path, cover_letter_path, job_description_path, match_score, match_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (job_title, company_name, job_url, resume_path, cover_letter_path, job_description_path, match_score, match_summary))
            
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
