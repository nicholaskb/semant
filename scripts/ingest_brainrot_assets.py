#!/usr/bin/env python3
"""
Ingest Brainrot assets using ImageIngestionAgent.

This script upgrades the asset ingestion process to use the agentic workflow,
ensuring proper KG tagging and Qdrant indexing with the 'brainrot_2025' project ID.

Usage:
    python scripts/ingest_brainrot_assets.py --uploads-dir uploads
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger
from agents.domain.image_ingestion_agent import ImageIngestionAgent
from agents.core.base_agent import AgentMessage

load_dotenv()

async def ingest_assets(
    uploads_dir: str = "uploads",
    project_id: str = "brainrot_2025",
    max_concurrent: int = 5
) -> int:
    """
    Ingest assets using ImageIngestionAgent.
    """
    local_dir = Path(uploads_dir)
    if not local_dir.exists():
        logger.error(f"Uploads directory not found: {local_dir}")
        return 1

    logger.info(f"Initializing ImageIngestionAgent for project: {project_id}")
    
    # Initialize agent
    agent = ImageIngestionAgent(
        agent_id="ingestion_worker",
        max_concurrent_downloads=max_concurrent,
        gcs_bucket_name=os.getenv("GCS_BUCKET_NAME") # Ensure this env var is set
    )
    await agent.initialize()

    # Construct request message
    message = AgentMessage(
        sender_id="cli_script",
        recipient_id="ingestion_worker",
        content={
            "action": "ingest_local_folder",
            "local_dir": str(local_dir),
            "gcs_prefix": "brainrot_uploads/", # Organize in a specific folder
            "image_type": "input", # Treat uploads as inputs
            "project_id": project_id,
            "extensions": ["png", "jpg", "jpeg", "webp", "gif"],
            "overwrite": False 
        },
        message_type="request",
        timestamp=datetime.utcnow().isoformat()
    )

    logger.info(f"Sending ingestion request for {local_dir}...")
    
    # Process message directly (bypassing router for this script)
    response = await agent._process_message_impl(message)
    
    if response.content.get("status") == "success":
        count = response.content.get("ingested_count", 0)
        logger.success(f"Successfully ingested {count} assets.")
        logger.info(f"Image URIs: {len(response.content.get('image_uris', []))}")
        return 0
    else:
        error = response.content.get("error", "Unknown error")
        logger.error(f"Ingestion failed: {error}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Brainrot assets via Agent")
    parser.add_argument("--uploads-dir", default="uploads", help="Directory containing images")
    parser.add_argument("--project-id", default="brainrot_2025", help="Project ID for KG tagging")
    parser.add_argument("--concurrent", type=int, default=5, help="Max concurrent uploads")
    
    args = parser.parse_args()
    
    try:
        exit_code = asyncio.run(ingest_assets(
            uploads_dir=args.uploads_dir,
            project_id=args.project_id,
            max_concurrent=args.concurrent
        ))
        sys.exit(exit_code)
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        sys.exit(1)

