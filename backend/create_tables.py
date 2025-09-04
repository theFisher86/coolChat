#!/usr/bin/env python3
"""Script to create SQLite tables using SQLAlchemy models"""

import os
import sys
from sqlalchemy import create_engine, text

# Set up basic Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

def create_tables():
    """Create all database tables using SQLAlchemy"""
    # Import models after setting path
    from models import Base
    from database import DATABASE_URL

    # Create engine
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    try:
        # Create all tables defined in models
        Base.metadata.create_all(bind=engine)
        print("[CoolChat] All tables created successfully using SQLAlchemy")

        # Verify tables exist
        with engine.connect() as conn:
            tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
            table_names = [row[0] for row in tables]
            print(f"[CoolChat] Tables found: {sorted(table_names)}")

    except Exception as e:
        print(f"[CoolChat] Error creating tables: {e}")
        raise

if __name__ == "__main__":
    print("[CoolChat] Creating SQLite tables...")
    try:
        create_tables()
        print("[CoolChat] Database setup complete!")
    except Exception as e:
        print(f"[CoolChat] Error: {e}")
        import traceback
        traceback.print_exc()