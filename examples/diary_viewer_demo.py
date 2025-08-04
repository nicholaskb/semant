"""examples/diary_viewer_demo.py

Run this script to:
1. Spin up a SensorAgent called `demo_viewer_agent` and write an initial diary entry.
2. Launch the FastAPI server (port 8000) so you can inspect the diary via the browser.

Usage:
    python examples/diary_viewer_demo.py

Then visit: http://localhost:8000/static/diary_viewer.html and enter `demo_viewer_agent`.
"""

import nest_asyncio
import asyncio, sys, pathlib
import uvicorn
from agents.core.data_handler_agent import SensorAgent

# Ensure repo root is on sys.path so `import main` works even if executed from elsewhere
repo_root = pathlib.Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from main import app

nest_asyncio.apply()

async def main():
    agent_id = "demo_viewer_agent"
    agent = SensorAgent(agent_id=agent_id)
    await agent.initialize()
    agent.write_diary("👋 Hello from diary viewer demo!", details={"note": "example"})
    print(f"Agent '{agent_id}' initialized and first diary entry written.")

    # Start server (non-blocking) so script continues
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    print("→ Open http://localhost:8000/static/diary_viewer.html and enter 'demo_viewer_agent'.")
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main()) 