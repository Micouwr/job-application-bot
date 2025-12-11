from pathlib import Path
from typing import List, Dict, Any
import sqlite3
from config.settings import DB_PATH

class ResumeModel:
    def __init__(self):
        self.db_path = DB_PATH
        self._init_database()
    
    def _init_database(self):
        """Initialize resume table if not exists"""
        with sqlite3.connect(self.db_path) as conn:
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
    
    def add_resume(self, file_path: str, name: str, is_active: bool = False) -> int:
        """Add a new resume to the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO resumes (name, file_path, is_active)
                VALUES (?, ?, ?)
            ''', (name, file_path, 1 if is_active else 0))
            conn.commit()
            return cursor.lastrowid
    
    def list_resumes(self) -> List[Dict[str, Any]]:
        """List all resumes"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM resumes ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_resume(self) -> Dict[str, Any]:
        """Get the currently active resume"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM resumes WHERE is_active = 1 LIMIT 1')
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def set_active_resume_by_path(self, file_path: str):
        """Set a resume as active by file path"""
        with sqlite3.connect(self.db_path) as conn:
            # Deactivate all others
            conn.execute('UPDATE resumes SET is_active = 0')
            # Activate selected
            conn.execute('UPDATE resumes SET is_active = 1 WHERE file_path = ?', (file_path,))
            conn.commit()
    
    def delete_resume_by_path(self, file_path: str):
        """Delete a resume by file path"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM resumes WHERE file_path = ?', (file_path,))
            conn.commit()

# Future-proofing: When upgrading to SQLAlchemy, inherit from declarative base
# and add relationships, validation, etc.
