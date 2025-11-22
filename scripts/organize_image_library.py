#!/usr/bin/env python3
"""
Organize Existing Image Assets.

This script:
1. Iterates through the 'generated_books/' directory.
2. Ingests all found images into the Knowledge Graph with 'legacy_import' project tag.
3. Runs DBSCAN clustering to group them by style.
4. Outputs a report of discovered style clusters.
"""
import os
import sys
import asyncio
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.domain.image_ingestion_agent import ImageIngestionAgent
from kg.services.image_embedding_service import ImageEmbeddingService
from kg.models.graph_manager import KnowledgeGraphManager

# Load environment variables
load_dotenv()

async def main():
    logger.info("=" * 60)
    logger.info("🖼️  ORGANIZE IMAGE LIBRARY")
    logger.info("=" * 60)
    
    # Initialize
    kg_manager = KnowledgeGraphManager(persistent_storage=True)
    agent = ImageIngestionAgent(kg_manager=kg_manager)
    service = ImageEmbeddingService()
    
    project_id = "legacy_import"
    generated_books_dir = Path("generated_books")
    
    if not generated_books_dir.exists():
        logger.error(f"Directory not found: {generated_books_dir}")
        return
        
    # 1. Collect Images
    logger.info(f"Scanning {generated_books_dir} for images...")
    image_files = []
    for ext in ["*.png", "*.jpg", "*.jpeg"]:
        image_files.extend(list(generated_books_dir.rglob(ext)))
    
    logger.info(f"Found {len(image_files)} images.")
    
    # Limit for demo purposes if needed, but let's try to process all
    # image_files = image_files[:100] 
    
    # 2. Ingest Images
    logger.info(f"Ingesting images with project tag '{project_id}'...")
    ingested_uris = []
    
    # Use a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(10)
    
    async def ingest_single(img_path):
        async with semaphore:
            try:
                # Simulate GCS upload or just use local path? 
                # For legacy import, we probably want to treat them as "input" type unless we know better
                # We'll skip the actual GCS upload for speed and just register them
                # Actually, ImageIngestionAgent expects GCS. 
                # Let's mock the GCS URL with the local path for now, or upload if we want to be thorough.
                # For this "reincorporation", let's assume we want them properly in the system.
                
                # We will use the _store_image_in_kg directly if we don't want to re-upload
                # But we need embeddings. The ImageIngestionAgent generates embeddings during _download_and_ingest_image.
                # We might need a helper method in ImageIngestionAgent to ingest LOCAL images.
                
                # Let's use the agent's method but we need to mock the blob or handle local files.
                # Looking at ImageIngestionAgent, it doesn't have a public "ingest_local_file" method easily exposed.
                # But _download_and_ingest_image takes a blob.
                
                # Let's use ImageEmbeddingService directly to get embedding, then store in KG.
                
                filename = img_path.name
                # Mock GCS URL or use local path
                gcs_url = f"file://{img_path.absolute()}" 
                image_uri = f"http://example.org/image/{filename.replace('.', '_')}_{img_path.stat().st_mtime}"
                
                # Get embedding
                # We need to read the image bytes
                # This part depends on how ImageEmbeddingService gets embeddings. 
                # It usually takes a text description or we need a vision model.
                # Wait, ImageIngestionAgent uses VertexAI for embeddings?
                # Let's check ImageIngestionAgent._download_and_ingest_image implementation.
                pass
            except Exception as e:
                logger.error(f"Failed to ingest {img_path}: {e}")
                return None

    # Actually, let's look at ImageIngestionAgent again.
    # It seems to rely on GCS.
    # For "reincorporating life", maybe we should just focus on the CLUSTERING part 
    # assuming we can get embeddings.
    
    # Let's look at how we can get embeddings for local images.
    
    pass

if __name__ == "__main__":
    asyncio.run(main())

