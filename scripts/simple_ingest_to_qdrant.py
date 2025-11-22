#!/usr/bin/env python3
"""Simple script to ingest images from uploads/ to Qdrant. No fancy checks, just works."""

import asyncio
from pathlib import Path
import httpx
from tqdm import tqdm

UPLOADS_DIR = Path("uploads")
API_URL = "http://localhost:8000/api/images/index"
EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

async def ingest_image(path: Path, client: httpx.AsyncClient):
    """Upload one image."""
    try:
        with open(path, "rb") as f:
            files = {"image_file": (path.name, f, "image/png")}
            data = {"image_type": "output", "store_in_kg": "true"}
            resp = await client.post(API_URL, files=files, data=data, timeout=300.0)
            resp.raise_for_status()
            return True
    except Exception:
        return False

async def main():
    # Find all images
    images = []
    for batch_dir in sorted(UPLOADS_DIR.glob("batch_*")):
        if batch_dir.is_dir():
            images.extend([p for p in batch_dir.iterdir() if p.suffix.lower() in EXTENSIONS])
    
    print(f"Found {len(images)} images to ingest")
    
    # Process them
    async with httpx.AsyncClient(timeout=300.0) as client:
        semaphore = asyncio.Semaphore(5)  # 5 concurrent
        
        async def process(img_path):
            async with semaphore:
                return await ingest_image(img_path, client)
        
        tasks = [process(img) for img in images]
        results = []
        
        with tqdm(total=len(tasks), desc="Ingesting", unit="img") as pbar:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                pbar.update(1)
    
    success = sum(results)
    print(f"\nDone! {success}/{len(images)} successful")

if __name__ == "__main__":
    asyncio.run(main())

