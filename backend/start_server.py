#!/usr/bin/env python3
"""Wrapper script to start the FastAPI server with proper import paths"""

import sys
import os

# Add current directory and parent directory to path to fix relative imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now import and run the main app
from backend.main import app
import uvicorn

if __name__ == "__main__":
    print("[CoolChat] Starting backend server on http://localhost:8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)