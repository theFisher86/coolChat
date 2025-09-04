#!/usr/bin/env python3
"""Database reset and rebuild script"""

import sys
import os
import shutil
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database import DB_PATH, create_tables, engine
from models import Base

def reset_database():
    """Reset the database by removing and recreating it"""
    print(f"[RESET] Resetting database at: {DB_PATH}")

    # Remove existing database if it exists
    if DB_PATH.exists():
        print("[RESET] Removing existing database file...")
        DB_PATH.unlink()
        print("[RESET] ✅ Database file removed")

    # Create fresh database
    print("[RESET] Creating new database...")
    create_tables()
    print("[RESET] ✅ Database reset complete!")

    # Verify tables exist
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"[RESET] Created tables: {tables}")

    if len(tables) >= 5:  # Should have characters, lorebooks, lore_entries, etc.
        print("[RESET] ✅ All expected tables created successfully")
        return True
    else:
        print("[RESET] ❌ Some tables may be missing")
        return False

def main():
    """Main function"""
    print("[RESET] Starting database reset...")

    # Confirm action
    print("[RESET] ⚠️  This will DELETE all existing data!")
    # Automatically proceed for troubleshooting
    print("[RESET] Continuing with reset...")

    try:
        success = reset_database()
        if success:
            print("\n[RESET] 🎉 Database has been successfully reset!")
            print("[RESET] You can now restart the server and import your lorebooks again.")
            return 0
        else:
            print("[RESET] ❌ Database reset incomplete")
            return 1
    except Exception as e:
        print(f"[RESET] ❌ Database reset failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)