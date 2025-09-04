#!/usr/bin/env python3
"""Database repair and corruption fix script"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models import Character, Lorebook, LoreEntry
from database import SessionLocal, get_db
import json

def fix_character_json_fields(db):
    """Fix corrupted JSON fields in characters table"""
    print("[FIX] Checking Character JSON fields...")

    # Get all characters
    characters = db.query(Character).all()
    fixed_count = 0

    for char in characters:
        needs_update = False

        # Fix alternate_greetings
        if char.alternate_greetings is None:
            char.alternate_greetings = []
            needs_update = True
        elif isinstance(char.alternate_greetings, str):
            try:
                # Try to parse if it's a JSON string
                if char.alternate_greetings.strip():
                    parsed = json.loads(char.alternate_greetings)
                    if isinstance(parsed, list):
                        char.alternate_greetings = parsed
                        needs_update = True
                    else:
                        char.alternate_greetings = []
                        needs_update = True
                else:
                    char.alternate_greetings = []
                    needs_update = True
            except (json.JSONDecodeError, TypeError):
                char.alternate_greetings = []
                needs_update = True

        # Fix tags
        if char.tags is None:
            char.tags = []
            needs_update = True
        elif isinstance(char.tags, str):
            try:
                if char.tags.strip():
                    parsed = json.loads(char.tags)
                    if isinstance(parsed, list):
                        char.tags = parsed
                        needs_update = True
                    else:
                        char.tags = []
                        needs_update = True
                else:
                    char.tags = []
                    needs_update = True
            except (json.JSONDecodeError, TypeError):
                char.tags = []
                needs_update = True

        # Fix extensions
        if char.extensions is None:
            char.extensions = {}
            needs_update = True
        elif isinstance(char.extensions, str):
            try:
                if char.extensions.strip():
                    parsed = json.loads(char.extensions)
                    if isinstance(parsed, dict):
                        char.extensions = parsed
                        needs_update = True
                    else:
                        char.extensions = {}
                        needs_update = True
                else:
                    char.extensions = {}
                    needs_update = True
            except (json.JSONDecodeError, TypeError):
                char.extensions = {}
                needs_update = True

        if needs_update:
            fixed_count += 1
            print(f"[FIX] Fixed character {char.id}: {char.name}")

    if fixed_count > 0:
        db.commit()
        print(f"[FIX] Fixed {fixed_count} character JSON fields")

    return fixed_count

def fix_lore_entry_json_fields(db):
    """Fix corrupted JSON fields in lore_entries table"""
    print("[FIX] Checking LoreEntry JSON fields...")

    # Get all lore entries
    entries = db.query(LoreEntry).all()
    fixed_count = 0

    for entry in entries:
        needs_update = False

        # Fix keywords
        if entry.keywords is None:
            entry.keywords = []
            needs_update = True
        elif isinstance(entry.keywords, str):
            try:
                if entry.keywords.strip():
                    parsed = json.loads(entry.keywords)
                    if isinstance(parsed, list):
                        entry.keywords = parsed
                        needs_update = True
                    else:
                        entry.keywords = []
                        needs_update = True
                else:
                    entry.keywords = []
                    needs_update = True
            except (json.JSONDecodeError, TypeError):
                entry.keywords = []
                needs_update = True

        # Fix secondary_keywords
        if entry.secondary_keywords is None:
            entry.secondary_keywords = []
            needs_update = True
        elif isinstance(entry.secondary_keywords, str):
            try:
                if entry.secondary_keywords.strip():
                    parsed = json.loads(entry.secondary_keywords)
                    if isinstance(parsed, list):
                        entry.secondary_keywords = parsed
                        needs_update = True
                    else:
                        entry.secondary_keywords = []
                        needs_update = True
                else:
                    entry.secondary_keywords = []
                    needs_update = True
            except (json.JSONDecodeError, TypeError):
                entry.secondary_keywords = []
                needs_update = True

        if needs_update:
            fixed_count += 1
            print(f"[FIX] Fixed lore entry {entry.id}: {entry.title}")

    if fixed_count > 0:
        db.commit()
        print(f"[FIX] Fixed {fixed_count} lore entry JSON fields")

    return fixed_count

def clean_invalid_lore_entries(db):
    """Remove lore entries with invalid data"""
    print("[FIX] Cleaning invalid lore entries...")

    # Get all lore entries
    entries = db.query(LoreEntry).all()
    removed_count = 0

    for entry in entries:
        # Remove entries with null or empty content
        if not entry.content or not entry.content.strip():
            try:
                db.delete(entry)
                removed_count += 1
                print(f"[FIX] Removed lore entry {entry.id}: empty content")
            except Exception as e:
                print(f"[FIX] Error removing entry {entry.id}: {e}")

    if removed_count > 0:
        db.commit()
        print(f"[FIX] Removed {removed_count} invalid lore entries")

    return removed_count

def check_json_errors_directly():
    """Check for JSON errors directly with SQL queries"""
    print("[FIX] Direct JSON validation...")

    db = SessionLocal()
    try:
        # Check for corrupted JSON in raw SQL
        corrupted_json = db.execute(text("""
            SELECT id, keywords, secondary_keywords
            FROM lore_entries
            WHERE keywords LIKE '{%' OR keywords LIKE '[%'
               OR secondary_keywords LIKE '{%' OR secondary_keywords LIKE '[%'
               OR COALESCE(keywords, '') = ''
               OR COALESCE(secondary_keywords, '') = ''
               OR keywords IS NULL
               OR secondary_keywords IS NULL
        """)).fetchall()

        if corrupted_json:
            print(f"[FIX] Found {len(corrupted_json)} potentially corrupted JSON fields")

            # Fix them with direct SQL updates
            for row in corrupted_json:
                entry_id = row[0]

                # Reset corrupted keywords to empty arrays
                try:
                    db.execute(text(f"""
                        UPDATE lore_entries
                        SET keywords = '[]'::jsonb,
                            secondary_keywords = '[]'::jsonb
                        WHERE id = {entry_id}
                    """))
                    print(f"[FIX] Fixed lore entry {entry_id} with direct SQL")
                except Exception as e:
                    print(f"[FIX] Error fixing entry {entry_id}: {e}")

            db.commit()
            print(f"[FIX] Fixed {len(corrupted_json)} entries with direct SQL updates")
            return len(corrupted_json)
        else:
            print("[FIX] No direct SQL JSON corruption found")

    except Exception as e:
        print(f"[FIX] Direct SQL check failed: {e}")
    finally:
        db.close()

    return 0

def main():
    """Main database repair function"""
    print("[FIX] Starting database repair...")

    # Check if database file exists (using correct database name from database.py)
    db_file = backend_dir / "app.db"
    if not db_file.exists():
        print(f"[ERROR] Database file not found: {db_file}")
        print(f"[FIX] Please ensure the server has been started at least once to create the database.")
        return 1

    # Create session
    db = SessionLocal()

    try:
        total_fixed = 0

        # Fix JSON fields
        fixed_chars = fix_character_json_fields(db)
        total_fixed += fixed_chars

        fixed_entries = fix_lore_entry_json_fields(db)
        total_fixed += fixed_entries

        # Clean invalid entries
        removed_entries = clean_invalid_lore_entries(db)
        total_fixed += removed_entries

        # Additional check with direct SQL
        direct_fixed = check_json_errors_directly()
        total_fixed += direct_fixed

        print(f"\n[FIX] Database repair complete!")
        print(f"[FIX] Total fixes applied: {total_fixed}")

        if total_fixed > 0:
            print("[FIX] ✅ Database has been repaired. You can now restart the server.")
        else:
            print("[FIX] ✅ No issues found in database.")

        return 0

    except Exception as e:
        print(f"[ERROR] Database repair failed: {e}")
        db.rollback()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)