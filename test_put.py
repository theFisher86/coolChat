import requests
import json

# First, check current state
print("=== Current State Check ===")

# Check lorebooks
print("\n--- Checking Lorebooks ---")
response = requests.get("http://localhost:8001/lorebooks")
print(f"Lorebooks: {response.json()}")

# Check lore list
print("\n--- Checking Lore Entries ---")
response = requests.get("http://localhost:8001/lore")
lore_entries = response.json()
print(f"Lore entries: {len(lore_entries)} entries")

# If no entries exist, create one via API
if not lore_entries:
    print("\n--- Creating Sample Lore Entry ---")
    sample_data = {
        "keyword": "sample keyword",
        "content": "sample content"
    }
    response = requests.post("http://localhost:8001/lore", headers={"Content-Type": "application/json"}, data=json.dumps(sample_data))
    print(f"Created: {response.json()}")
    created_entry = response.json()

    # Now test the PUT endpoint
    print("\n=== Testing PUT Endpoint ===")
    url = f"http://localhost:8001/lorebooks/entries/{created_entry['id']}"

    # Test with various data payloads to confirm functionality
    data = [
        {"title": "Test", "content": "Test content"},
        {"title": "Another Test", "content": "Another content", "keywords": ["key1", "key2"]},
        {"keywords": ["frontend"], "secondaryKeywords": ["test"], "logic": "AND ALL"},
        {"secondaryKeywords": ["backend"], "trigger": 75.0, "order": 5.0}
    ]

    for i, test_data in enumerate(data):
        print(f"\n--- Test {i+1}: {test_data} ---")
        try:
            response = requests.put(url, headers={"Content-Type": "application/json"}, data=json.dumps(test_data))
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
else:
    print(f"\nUsing existing entry ID: {lore_entries[0]['id']}")
    url = f"http://localhost:8001/lorebooks/entries/{lore_entries[0]['id']}"

    # Test the PUT endpoint with a simple payload
    print("\n=== Testing PUT Endpoint ===")
    test_data = {"title": "Updated Title"}
    response = requests.put(url, headers={"Content-Type": "application/json"}, data=json.dumps(test_data))
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")