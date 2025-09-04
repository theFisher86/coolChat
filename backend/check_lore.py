#!/usr/bin/env python3

import sqlite3
import os

db_path = os.path.join('.', 'app.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("LOREBOOKS IN DATABASE:")
cursor.execute('SELECT id, name, description FROM lorebooks')
lorebooks = cursor.fetchall()

if not lorebooks:
    print("No lorebooks found!")
else:
    for lb_id, name, description in lorebooks:
        print(f"ID {lb_id}: {name} - {description if description else '(no description)'}")

print("\nLORE ENTRIES IN DATABASE:")
cursor.execute('SELECT id, title, content FROM lore_entries ORDER BY id DESC LIMIT 10')
entries = cursor.fetchall()

if not entries:
    print("No lore entries found!")
else:
    for entry_id, title, content in entries:
        print(f"ID {entry_id}: {title[:50] if title else '(no title)'} - {content[:50]}...")

cursor.execute('SELECT COUNT(*) FROM lore_entries')
count = cursor.fetchone()[0]
print(f"\nTotal lore entries: {count}")

cursor.close()
conn.close()