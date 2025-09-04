#!/usr/bin/env python3
"""Standalone migration of chat histories to SQLite"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database setup
backend_dir = Path(__file__).parent
DB_PATH = backend_dir / "app.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Models
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(255), primary_key=True, index=True)
    name = Column(String(255), default="Chat")
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String(255), ForeignKey("chat_sessions.id"), index=True)
    role = Column(String(50), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=True)
    image_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Utility function for loading JSON files
def load_json(filename: str, default=None):
    """Load data from a JSON file."""
    try:
        file_path = backend_dir / filename
        if not file_path.exists():
            return default
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    print("[CoolChat] Tables created/verification completed")

def _create_chat_session(session_id: str, name: str = "Chat") -> None:
    """Create a new chat session in SQLite."""
    db = SessionLocal()
    try:
        # Check if session already exists
        existing = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not existing:
            chat_session = ChatSession(id=session_id, name=name)
            db.add(chat_session)
            db.commit()
    except Exception as e:
        print(f"[CoolChat] Error creating chat session: {e}")
        db.rollback()
    finally:
        db.close()

def _save_chat_message(session_id: str, role: str, content: str, image_url: str = None) -> None:
    """Save a chat message to SQLite."""
    db = SessionLocal()
    try:
        # Ensure chat session exists
        _create_chat_session(session_id)

        # Create message
        message = ChatMessage(
            chat_id=session_id,
            role=role,
            content=content,
            image_url=image_url
        )
        db.add(message)
        db.commit()
    except Exception as e:
        print(f"[CoolChat] Error saving chat message: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("[CoolChat] Starting standalone migration...")

    # Create tables first
    create_tables()

    # Load existing JSON histories
    _chat_histories = load_json("histories.json", {})

    if not _chat_histories:
        print("[CoolChat] No chat histories to migrate")
    else:
        print(f"[CoolChat] Migrating {len(_chat_histories)} chat sessions to SQLite...")

        for session_id, chat_history in _chat_histories.items():
            try:
                # Create session (if not exists)
                _create_chat_session(session_id, f"Session {session_id}")

                # Save all messages
                for msg in chat_history:
                    _save_chat_message(
                        session_id=session_id,
                        role=msg.get("role", "assistant"),
                        content=msg.get("content", ""),
                        image_url=msg.get("image_url")
                    )

                print(f"[CoolChat] Migrated {len(chat_history)} messages for session {session_id}")

            except Exception as e:
                print(f"[CoolChat] Error migrating session {session_id}: {e}")

    print("[CoolChat] Migration completed successfully!")