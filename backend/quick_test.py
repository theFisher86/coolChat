#!/usr/bin/env python3
"""Quick test to verify API endpoints"""
import time
import subprocess
import sys

def test_endpoints():
    # Test the working backend directly
    print('Testing lore API with Python requests...')

    try:
        # Import and call the api test function directly
        from test_server import test_lore_api
        result = test_lore_api()
        print(f"✅ Test completed successfully: {result}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_endpoints()