#!/usr/bin/env python3
"""Test script to verify database-backed configuration works"""

import os
import sys

# Add current directory and parent directory to path to fix relative imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now import our modules
from backend.config import load_config, save_config, AppConfig
from backend.database import SessionLocal, create_tables
from backend.models import AppSettings

def test_config_db():
    print("Creating tables...")
    create_tables()

    print("Testing config loading...")
    config = load_config()
    print(f"Loaded config: {config.active_provider}")

    print("Testing config saving...")
    # Update some setting
    config.active_provider = "gemini"  # or whatever value you want
    save_config(config)

    print("Testing config reload...")
    config2 = load_config()
    print(f"Reloaded config: {config2.active_provider}")

    print("Checking database...")
    with SessionLocal() as db:
        setting = db.query(AppSettings).filter(AppSettings.key == "main_config").first()
        if setting:
            print(f"Database has config: {bool(setting.value)}")
            print(f"Database config keys: {list(setting.value.keys())[:5]}...")  # First 5 keys
        else:
            print("No config found in database")

    print("Testing config.json backup...")
    if os.path.exists("../config.json"):
        print("config.json exists and was updated")
        with open("../config.json", "r") as f:
            data = f.read()
            print(f"config.json size: {len(data)} characters")
    else:
        print("config.json backup not found")

    print("Test completed successfully!")

if __name__ == "__main__":
    test_config_db()