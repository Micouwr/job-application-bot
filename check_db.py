import sqlite3
from config.settings import DB_PATH

# Connect to the database
conn = sqlite3.connect(DB_PATH)
cursor = conn.execute('SELECT id, job_title, company_name, job_description_path FROM applications ORDER BY created_at DESC')
rows = cursor.fetchall()

print("Applications in database:")
for i, row in enumerate(rows):
    print(f"Record {i+1}: ID={row[0]}, Title='{row[1]}', Company='{row[2]}', JobDescPath='{row[3]}'")

conn.close()