#!/usr/bin/env python3
"""Script to create SQLite tables with proper model imports"""

import os
import sys
import importlib.util
import sqlite3

# Set up basic Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

def create_tables_direct():
    """Create tables directly without import issues"""
    db_path = os.path.join(backend_dir, "app.db")

    # Create SQLite tables directly using SQL
    sql_commands = [
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
        );
        """
    ]

    conn = sqlite3.connect(db_path)
    try:
        for sql in sql_commands:
            conn.execute(sql.strip())
        conn.commit()
        print("[CoolChat] Tables created successfully using direct SQL")
    except sqlite3.Error as e:
        print(f"[CoolChat] SQLite error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        create_tables_direct()
        print("[CoolChat] Database setup complete!")
    except Exception as e:
        print(f"[CoolChat] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("[CoolChat] Creating SQLite tables...")
    try:
        create_tables()
        print("[CoolChat] Tables created successfully")

        # Verify tables exist
        from sqlalchemy import text
        with engine.connect() as conn:
            tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
            table_names = [row[0] for row in tables]
            print(f"[CoolChat] Tables found: {table_names}")

    except Exception as e:
        print(f"[CoolChat] Error creating tables: {e}")
        traceback.print_exc()