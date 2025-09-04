#!/usr/bin/env python3

import requests
import json

# API endpoints - using port 5173 since uvicorn might be running on different port
base_url = 'http://localhost:8001'

# Create a lorebook with inline entries
lorebook_data = {
    'name': 'Eldoria',
    'description': 'Ancient kingdom of magic and mystery',
    'entries': [{
        'keyword': 'The Crystal Chamber',
        'content': 'Deep underground lies the Crystal Chamber, a massive cavern filled with glowing crystals that power the kingdom of Eldoria. These crystals hold immense magical energy.',
        'keywords': ['crystal', 'chamber', 'underground', 'magic', 'eldoria'],
        'secondary_keywords': ['cavern', 'glowing', 'power', 'kingdom'],
        'logic': 'AND ANY',
        'trigger': 100.0,
        'order': 0.0
    }]
}

try:
    print("Creating sample lorebook with API...")
    response = requests.post(f'{base_url}/lorebooks', json=lorebook_data)
    response.raise_for_status()
    result = response.json()
    print('Successfully created sample lore data:')
    print(f'ID: {result["id"]}, Name: {result["name"]}')
    print('Lore entries:')
    for entry in result.get('entries', []):
        print(f'  ID: {entry["id"]}, Title: {entry.get("keyword", entry.get("title", "N/A"))}')
except requests.exceptions.RequestException as e:
    print(f'Failed to create sample data: {e}')
    if hasattr(e.response, 'text'):
        print(f'Response: {e.response.text}')
except Exception as e:
    print(f'Error: {e}')