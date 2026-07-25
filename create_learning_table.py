"""
Create learning_annotations table for FairRead Learn feature.
Run this once to initialize the table.
"""

import sqlite3
import os

db_path = 'static/database.db'

if not os.path.exists(db_path):
    print(f"Error: Database file not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create learning_annotations table
try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            user_id INTEGER,
            target_language TEXT NOT NULL DEFAULT 'en',
            term TEXT NOT NULL,
            term_type TEXT NOT NULL,
            definition TEXT,
            english_meaning TEXT,
            example_sentence TEXT,
            difficulty TEXT,
            part_of_speech TEXT,
            grammar_note TEXT,
            article_language TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES Chatlog(rowid)
        )
    """)
    conn.commit()
    print("[OK] learning_annotations table created successfully!")
    
    # Show table info
    cursor.execute("PRAGMA table_info(learning_annotations)")
    columns = cursor.fetchall()
    print("\nTable schema:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
except sqlite3.OperationalError as e:
    if "already exists" in str(e):
        print("[OK] learning_annotations table already exists!")
    else:
        print(f"[ERROR] {e}")
        exit(1)
finally:
    conn.close()

print("\n[OK] Database initialization complete!")
