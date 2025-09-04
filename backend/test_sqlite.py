#!/usr/bin/env python3
"""Test script to verify SQLite functionality"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from database import SessionLocal, create_tables
from models import ChatSession, ChatMessage
from main import _create_chat_session, _save_chat_message, _load_chat_session, _migrate_chat_histories_to_sqlite

def test_basic_sqlite_operations():
    print("=== Testing Basic SQLite Operations ===")

    # Test create tables
    print("1. Creating tables...")
    create_tables()

    # Test session creation
    print("2. Creating chat session...")
    test_session_id = "test_session_123"
    _create_chat_session(test_session_id, "Test Session")

    # Test message saving
    print("3. Saving messages...")
    _save_chat_message(test_session_id, "user", "Hello, this is a test message!")
    _save_chat_message(test_session_id, "assistant", "Hello! This is a test response.")

    # Test message loading
    print("4. Loading messages...")
    messages = _load_chat_session(test_session_id)
    print(f"   Loaded {len(messages)} messages:")
    for msg in messages:
        print(f"   - {msg['role']}: {msg['content']}")

    # Test list all sessions using direct SQLAlchemy query
    print("5. Listing all sessions...")
    db = SessionLocal()
    try:
        sessions = db.query(ChatSession).all()
        print(f"   Found {len(sessions)} sessions:")
        for session in sessions:
            print(f"   - {session.id}: {session.name}")
    except Exception as e:
        print(f"   Error listing sessions: {e}")
    finally:
        db.close()

    print("=== SQLite Tests Completed Successfully! ===")

if __name__ == "__main__":
    test_basic_sqlite_operations()