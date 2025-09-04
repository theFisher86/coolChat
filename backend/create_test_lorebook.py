#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(__file__))  # For absolute imports

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Lorebook, LoreEntry
import random
import json
from faker import Faker

# Initialize Faker for generating diverse content
fake = Faker()

def generate_lore_entry_data(index):
    """Generate diverse test data for a lore entry"""

    # Categories for varied content
    categories = [
        "magic_systems", "characters", "locations", "history", "creatures",
        "weapons", "guilds", "magic_items", "lore_families", "quests",
        "artifacts", "races", "professions", "events", "dieties"
    ]

    category = random.choice(categories)

    # Generate title
    if category == "magic_systems":
        words = fake.words(nb=2, ext_word_list=['Arcane', 'Divine', 'Elemental', 'Mystic', 'Ancient'])
        title = f"Magic System {index}: {words[0].capitalize()} {words[1].capitalize()}"
    elif category == "characters":
        title = f"{fake.first_name()} {fake.last_name()}, {fake.job()}"
    elif category == "locations":
        location_words = fake.words(nb=1, ext_word_list=['City', 'Castle', 'Mountain', 'Forest', 'Lake'])
        title = f"The {fake.word(ext_word_list=['Misty', 'Crystal', 'Ancient', 'Forgotten', 'Eternal'])} {location_words[0]}".capitalize()
    elif category == "history":
        history_words = fake.words(nb=1, ext_word_list=['War', 'Revolution', 'Eclipse', 'Prophecy', 'Council'])
        title = f"The {fake.word().capitalize()} {history_words[0]}".capitalize()
    elif category == "creatures":
        creature_words = fake.words(nb=1, ext_word_list=['Beast', 'Spirit', 'Guardian', 'Monster', 'Dragon'])
        title = f"{fake.word().capitalize()} {creature_words[0]}"
    elif category == "weapons":
        weapon_words = fake.words(nb=1, ext_word_list=['Blade', 'Hammer', 'Bow', 'Staff', 'Sword'])
        title = f"The {fake.word().capitalize()} {weapon_words[0]}"
    elif category == "guilds":
        guild_words = fake.words(nb=2, ext_word_list=['Mystic', 'Warriors', 'Merchants', 'Thieves', 'Casters', 'Hunters'])
        title = f"Guild of {guild_words[0]} {guild_words[1]}"
    elif category == "magic_items":
        magic_item_words = fake.words(nb=1, ext_word_list=['Amulet', 'Ring', 'Crown', 'Orb', 'Tome'])
        title = f"{fake.word().capitalize()} {magic_item_words[0]}"
    elif category == "lore_families":
        title = f"House {fake.last_name().capitalize()}"
    elif category == "quests":
        quest_words = fake.words(nb=1, ext_word_list=['Stone', 'Crystal', 'Sword', 'Treasure', 'Artifact'])
        title = f"Quest for the {fake.word().capitalize()} {quest_words[0]}"
    elif category == "artifacts":
        artifact_words = fake.words(nb=2, ext_word_list=['Lost', 'Ancient', 'Forbidden', 'Divine', 'Eternal', 'Misty', 'Crystal'])
        title = f"The {' '.join(artifact_words)}"
    elif category == "races":
        race_words1 = fake.words(nb=1, ext_word_list=['Elven', 'Dwarven', 'Human', 'Orcish', 'Draconic'])
        race_words2 = fake.words(nb=1, ext_word_list=['Kingdom', 'Empire', 'Migration', 'Culture', 'Tradition'])
        title = f"The {race_words1[0]} {race_words2[0]}"
    elif category == "professions":
        profession_words = fake.words(nb=1, ext_word_list=['Guild', 'Code', 'Secret', 'Ritual', 'Tradition'])
        job_parts = fake.job().split()
        job_part = job_parts[1] if len(job_parts) > 1 else job_parts[0]
        title = f"The {job_part}'s {profession_words[0]}"
    elif category == "events":
        event_words1 = fake.words(nb=1, ext_word_list=['Great', 'Legendary', 'Catastrophic', 'Mysterious', 'Divine'])
        event_words2 = fake.words(nb=1, ext_word_list=['Festival', 'Cataclysm', 'Revelation', 'Conclave', 'Battle'])
        title = f"The {event_words1[0]} {event_words2[0]}"
    elif category == "dieties":
        deity_words1 = fake.words(nb=1, ext_word_list=['God', 'Goddess', 'Deity'])
        deity_words2 = fake.words(nb=1, ext_word_list=['Wisdom', 'War', 'Love', 'Death', 'Nature'])
        title = f"{fake.first_name()}, {deity_words1[0]} of {deity_words2[0]}"
    else:
        other_words = fake.words(nb=3)
        title = f"Lore Entry {index}: {' '.join(other_words)}"

    # Generate content with varying lengths
    content_length = random.choices(
        [50, 100, 200, 500, 1000, 2000],
        weights=[10, 20, 30, 20, 15, 5]  # Favor medium-length entries
    )[0]

    if category == "magic_systems":
        magic_words1 = fake.words(nb=2)
        magic_words2 = fake.words(nb=3, ext_word_list=['energy', 'essence', 'power', 'mana', 'soul', 'spirit'])
        magic_words3 = fake.words(nb=1, ext_word_list=['discovered', 'created', 'revealed', 'bestowed'])
        magic_words4 = fake.words(nb=1, ext_word_list=['Great War', 'Ancient Age', 'First Era', 'Dark Times'])
        content = f"""The magic system of {' '.join(magic_words1)} revolves around {' '.join(magic_words2)}. Practitioners can {fake.sentence()}. This system was {magic_words3[0]} by {fake.name()} during the {magic_words4[0]}.

{fake.paragraph(nb_sentences=random.randint(3, 8))}

{fake.paragraph(nb_sentences=random.randint(2, 6))}

{fake.paragraph(nb_sentences=random.randint(1, 4))}"""
    else:
        content = fake.paragraphs(nb=random.randint(int(content_length/100), int(content_length/50)))

        if isinstance(content, list):
            content = '\n\n'.join(content)

        # Ensure minimum length
        while len(content) < content_length:
            content += '\n\n' + fake.paragraph(nb_sentences=random.randint(3, 8))

        # Ensure maximum length
        content = content[:content_length] + ('...' if len(content) > content_length else '')

    # Generate keywords
    primary_keywords = set()

    # Category-specific keywords
    if category == "magic_systems":
        primary_keywords.update(["magic", "spell", "enchantment", "arcane", "mana", "ritual"])
    elif category == "characters":
        primary_keywords.update([fake.first_name().lower(), fake.last_name().lower(), "character", "person", fake.job().lower()])
    elif category == "locations":
        primary_keywords.update(["location", fake.city(), fake.country(), "place", "area", "territory"])
    elif category == "history":
        primary_keywords.update(["history", "past", "event", "war", "battle", "ancient", "legend"])
    elif category == "creatures":
        primary_keywords.update(["creature", "monster", "beast", "animal", "mythical", "legendary"])
    elif category == "weapons":
        primary_keywords.update(["weapon", "blade", "sword", "equipment", "combat", "tool"])
    elif category == "guilds":
        primary_keywords.update(["guild", "organization", "group", "association", "society"])
    elif category == "magic_items":
        primary_keywords.update(["artifact", "magical_item", "treasure", "relic", "item"])

    # Add some generic and variant keywords
    additional_keywords = [
        "adventure", "quest", "kingdom", "empire", "town", "city", "village", "castle",
        "forest", "mountain", "river", "lake", "ocean", "desert", "plains", "valley",
        "ancient", "mysterious", "powerful", "magical", "cursed", "blessed", "sacred",
        "warrior", "mage", "rogue", "cleric", "paladin", "ranger", "sorcerer",
        fake.word(), fake.word(), fake.word()
    ]

    # Add 2-5 additional random keywords
    for _ in range(random.randint(2, 5)):
        primary_keywords.add(random.choice(additional_keywords))

    primary_keywords = list(primary_keywords)
    random.shuffle(primary_keywords)

    # Secondary keywords (less important)
    secondary_keywords = []
    secondary_pool = [
        "detail", "info", "note", "mention", "reference", "aspect", "element",
        "feature", "attribute", "property", "quality", "characteristic",
        fake.word(), fake.word(), fake.word(), fake.word()
    ]

    for _ in range(random.randint(1, 3)):
        secondary_keywords.append(random.choice(secondary_pool))

    # Logic settings with different strategies
    logic_options = ["AND ANY", "AND ALL", "NOT ANY", "NOT ALL"]
    logic = random.choices(logic_options, weights=[60, 20, 10, 10])[0]

    # Trigger values (mostly high for visibility)
    trigger = random.choices(
        [100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 25.0, 10.0, 0.0],
        weights=[20, 15, 15, 10, 10, 10, 5, 3, 1]
    )[0]

    # Order values for sorting
    order = random.uniform(-10.0, 10.0)

    return {
        "title": title,
        "content": content,
        "keywords": primary_keywords,
        "secondary_keywords": secondary_keywords,
        "logic": logic,
        "trigger": trigger,
        "order": order
    }

def create_test_lorebook():
    """Create a test lorebook with 200+ diverse entries"""

    print("[CoolChat] Creating test lorebook with 200+ entries...")

    db = SessionLocal()

    try:
        # Create or find test lorebook
        test_lorebook = db.query(Lorebook).filter(Lorebook.name == "Test Lorebook - Performance").first()

        if test_lorebook:
            print(f"Found existing test lorebook with ID {test_lorebook.id}, clearing existing entries...")

            # Delete existing entries
            entries_count = db.query(LoreEntry).filter(LoreEntry.lorebook_id == test_lorebook.id).count()
            db.query(LoreEntry).filter(LoreEntry.lorebook_id == test_lorebook.id).delete()

            print(f"Cleared {entries_count} existing entries")
        else:
            print("Creating new test lorebook...")
            test_lorebook = Lorebook(
                name="Test Lorebook - Performance",
                description="Large test dataset for pagination and performance verification (200+ entries)"
            )
            db.add(test_lorebook)
            db.commit()
            db.refresh(test_lorebook)

        print(f"Using lorebook ID: {test_lorebook.id}")

        # Generate and insert 200+ entries in batches
        batch_size = 50
        total_entries = 250  # Slightly more than 200 for better testing

        print(f"Generating {total_entries} lore entries...")

        created_entries = []

        for batch_start in range(0, total_entries, batch_size):
            batch_end = min(batch_start + batch_size, total_entries)
            batch_entries = []

            print(f"Processing batch {batch_start}-{batch_end}...")

            for i in range(batch_start, batch_end):
                entry_data = generate_lore_entry_data(i)

                entry = LoreEntry(
                    lorebook_id=test_lorebook.id,
                    title=entry_data["title"],
                    content=entry_data["content"],
                    keywords=entry_data["keywords"],
                    secondary_keywords=entry_data["secondary_keywords"],
                    logic=entry_data["logic"],
                    trigger=entry_data["trigger"],
                    order=entry_data["order"]
                )

                batch_entries.append(entry)
                created_entries.append(entry)

            # Add batch to database
            db.add_all(batch_entries)
            db.commit()

            print(f"Committed batch of {len(batch_entries)} entries")

        print("\n" + "="*70)
        print("TEST LOREBOOK CREATED SUCCESSFULLY!")
        print("="*70)
        print(f"Total entries created: {len(created_entries)}")
        print(f"Lorebook ID: {test_lorebook.id}")
        print(f"Lorebook Name: {test_lorebook.name}")

        # Statistics
        keyword_counts = {}
        logic_counts = {}
        trigger_ranges = {"full": 0, "high": 0, "medium": 0, "low": 0}

        for entry in created_entries:
            for kw in entry.keywords:
                if kw not in keyword_counts:
                    keyword_counts[kw] = 0
                keyword_counts[kw] += 1

            logic_counts[entry.logic.upper()] = logic_counts.get(entry.logic.upper(), 0) + 1

            if entry.trigger == 100.0:
                trigger_ranges["full"] += 1
            elif entry.trigger >= 70.0:
                trigger_ranges["high"] += 1
            elif entry.trigger >= 40.0:
                trigger_ranges["medium"] += 1
            else:
                trigger_ranges["low"] += 1

        print("\nDATA STATISTICS:")
        print(f"- Total unique keywords: {len(keyword_counts)}")
        print(f"- Most common keywords: {sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]}")
        print(f"- Logic distribution: {logic_counts}")
        print(f"- Trigger ranges: {trigger_ranges}")
        print(".0f")

        # Test the API by querying some entries
        print("\nTESTING API ACCESS:")
        test_entries = db.query(LoreEntry).filter(LoreEntry.lorebook_id == test_lorebook.id).limit(3).all()

        for i, entry in enumerate(test_entries):
            print(f"\nEntry {i+1}:")
            print(f"  Title: {entry.title}")
            print(f"  Keywords: {entry.keywords[:3]}...")  # Show first 3 keywords
            print(f"  Content length: {len(entry.content)} characters")
            print(f"  Logic: {entry.logic}")
            print(f"  Trigger: {entry.trigger}")
            print(f"  Order: {round(entry.order, 2)}")

    except Exception as e:
        db.rollback()
        print(f"Error creating test lorebook: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_lorebook()