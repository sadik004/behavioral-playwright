"""
Reddit Login Session Exporter (Workspace Root Runner).
Runs the interactive login exporter from Reddit.mcp.
"""

import sys
import os
from pathlib import Path

# Add Reddit.mcp/src to path
reddit_src = Path(__file__).parent.parent / "Reddit.mcp" / "src"
scripts_dir = Path(__file__).parent.parent / "Reddit.mcp" / "scripts"
if str(reddit_src) not in sys.path:
    sys.path.insert(0, str(reddit_src))
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from login import export_reddit_session
import asyncio

if __name__ == "__main__":
    default_output = Path(__file__).resolve().parent.parent / "Reddit.mcp" / "storage_state.json"
    out_file = sys.argv[1] if len(sys.argv) > 1 else str(default_output)
    asyncio.run(export_reddit_session(out_file))
