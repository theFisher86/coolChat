#!/usr/bin/env python3

import sqlite3
import json

conn = sqlite3.connect('app.db')
c = conn.cursor()

# Insert a sample lorebook
print("Creating sample lorebook...")
c.execute('''INSERT INTO lorebooks (name, description, created_at, updated_at)
             VALUES (?, ?, datetime('now'), datetime('now'))''', ('Eldoria', 'Ancient kingdom of magic'))

lb_id = c.lastrowid
print(f"Created lorebook with ID {lb_id}")

# Insert a sample lore entry
print("Creating sample lore entry...")
c.execute('''INSERT INTO lore_entries
             (lorebook_id, title, content, keywords, secondary_keywords, logic, trigger, "order", created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))''',
         (lb_id, 'The Crystal Chamber', 'Deep underground lies the Crystal Chamber, a massive cavern filled with glowing crystals that power the kingdom.', '["crystal", "chamber", "underground"]', '[]', 'AND ANY', 100.0, 0.0))

entry_id = c.lastrowid
print(f"Created lore entry with ID {entry_id}")

conn.commit()
c.close()
conn.close()

print(f"\nSAMPLE DATA CREATED:")
print(f"- Lorebook ID: {lb_id}, Name: Eldoria")
print(f"- Lore entry ID: {entry_id}, Title: The Crystal Chamber")

print("\nYou can now edit this entry to test the update functionality!")