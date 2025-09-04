#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Lorebook, LoreEntry

def create_sample_data():
    """Create sample lore data using SQLAlchemy."""

    db = SessionLocal()

    try:
        # Check if sample data already exists
        existing_lorebooks = db.query(Lorebook).count()
        if existing_lorebooks > 0:
            print("Sample data already exists. Skipping creation.")
            return

        # Create sample lorebook
        print("Creating sample lorebook...")
        lorebook = Lorebook(
            name="Eldoria",
            description="Ancient kingdom of magic and mystery"
        )
        db.add(lorebook)
        db.flush()  # Get the ID

        print(f"Created lorebook with ID {lorebook.id}")

        # Create sample lore entry
        print("Creating sample lore entry...")
        lore_entry = LoreEntry(
            lorebook_id=lorebook.id,
            title="The Crystal Chamber",
            content="Deep underground lies the Crystal Chamber, a massive cavern filled with glowing crystals that power the kingdom of Eldoria. These crystals hold immense magical energy.",
            keywords=["crystal", "chamber", "underground", "magic", "eldoria"],
            secondary_keywords=["cavern", "glowing", "power", "kingdom"],
            logic="AND ANY",
            trigger=100.0,
            order=0.0
        )
        db.add(lore_entry)
        db.flush()

        print(f"Created lore entry with ID {lore_entry.id}")

        # Commit all changes
        db.commit()

        print("\n" + "="*50)
        print("SAMPLE DATA CREATED:")
        print(f"- Lorebook ID: {lorebook.id}, Name: {lorebook.name}")
        print(f"- Lore entry ID: {lore_entry.id}, Title: {lore_entry.title}")
        print("="*50)

        print("\nYou can now test the lore system!")
        print("- GET /lorebooks to see the lorebook")
        print("- PUT /lorebooks/entries/{entry_id} to update the entry")
        print("- Use frontend to edit the 'The Crystal Chamber' entry")

    except Exception as e:
        db.rollback()
        print(f"Error creating sample data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_data()

