"""

Main entry point for the Travel Agent API.

Run with: python src/main.py
Or with unicorn: uvicorn src.api.server:app --reload
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0", # Listen on all network interfaces
        port=8000,
        reload=True, # Auto-reload on code changes (development only)
        log_level="info"
    )