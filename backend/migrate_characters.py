#!/usr/bin/env python3
"""Migrate existing JSON characters into the SQLite database."""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from storage import load_json
from database import SessionLocal
from models import Character


def migrate() -> None:
    data = load_json("characters.json", {"items": []})
    items = data.get("items") or []
    if not items:
        print("[migrate] No characters found in JSON")
        return
    db = SessionLocal()
    try:
        existing = db.query(Character).count()
        if existing:
            print(f"[migrate] Database already has {existing} characters; skipping")
            return
        for item in items:
            item = dict(item)
            item.pop("lorebook_ids", None)
            try:
                char = Character(**item)
                db.add(char)
            except Exception as e:
                print(f"[migrate] Skipping character {item.get('id')}: {e}")
        db.commit()
        print(f"[migrate] Migrated {len(items)} characters")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
