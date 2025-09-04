"""
Debug utility module for CoolChat backend.

Loads and manages debug configurations from debug.json file.
"""

import json
import os
from typing import Dict, Any


class DebugLogger:
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self):
        """Load debug configuration from debug.json file."""
        debug_file = os.path.join(os.path.dirname(__file__), "..", "debug.json")
        try:
            with open(debug_file, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load debug.json: {e}")
            # Default config if file can't be loaded
            self.config = {
                "backend": {
                    "tool_calls": True,
                    "llm_requests": False,
                    "llm_responses": False,
                    "database_operations": False,
                    "file_operations": False,
                    "performance": False
                },
                "enabled": True
            }

    def is_enabled(self, category: str) -> bool:
        """Check if a specific debug category is enabled."""
        if not self.config.get("enabled", True):
            return False

        backend_config = self.config.get("backend", {})
        return backend_config.get(category, False)

    def log(self, category: str, message: str, *args):
        """Log a message if the category is enabled."""
        if self.is_enabled(category):
            print(f"[DEBUG {category.upper()}] {message}", *args)

    def debug_tool_calls(self, message: str):
        """Log tool call debugging."""
        self.log("tool_calls", message)

    def debug_llm_requests(self, message: str):
        """Log LLM request debugging."""
        self.log("llm_requests", message)

    def debug_llm_responses(self, message: str):
        """Log LLM response debugging."""
        self.log("llm_responses", message)

    def debug_db(self, message: str):
        """Log database operation debugging."""
        self.log("database_operations", message)

    def debug_files(self, message: str):
        """Log file operation debugging."""
        self.log("file_operations", message)

    def debug_perf(self, message: str):
        """Log performance debugging."""
        self.log("performance", message)


# Global debug logger instance
_debug_logger = None

def get_debug_logger() -> DebugLogger:
    """Get the global debug logger instance."""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger()
    return _debug_logger

def debug_log(category: str, message: str, *args):
    """Convenience function for debug logging."""
    logger = get_debug_logger()
    logger.log(category, message, *args)