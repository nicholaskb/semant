#!/usr/bin/env python3
"""
Ingest images from uploads/ directory (batched images) into Qdrant.

This script processes images from the uploads/ directory that were downloaded
from GCS and batched for ingestion.

Usage:
    python scripts/ingest_uploads_to_qdrant.py
    python scripts/ingest_uploads_to_qdrant.py --uploads-dir uploads --batch-size 50
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from tqdm import tqdm

# Load environment variables
load_dotenv()

console = Console()

# API endpoint
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
INDEX_ENDPOINT = f"{API_BASE_URL}/api/images/index"

# Image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def find_images_in_uploads(uploads_dir: Path) -> Dict[str, List[Path]]:
    """Find all images in uploads directory, organized by batch."""
    images = {}
    
    if not uploads_dir.exists():
        console.print(f"[red]✗ Directory {uploads_dir} does not exist[/red]")
        return images
    
    # Find all batch directories
    batch_dirs = sorted([d for d in uploads_dir.iterdir() if d.is_dir() and d.name.startswith("batch_")])
    
    for batch_dir in batch_dirs:
        batch_images = []
        for image_path in batch_dir.iterdir():
            if image_path.is_file() and image_path.suffix.lower() in IMAGE_EXTENSIONS:
                batch_images.append(image_path)
        
        if batch_images:
            images[batch_dir.name] = batch_images
    
    return images


async def index_image(
    image_path: Path,
    image_type: str = "output",  # Default to output since these are generated images
    store_in_kg: bool = True,
    client: Optional[httpx.AsyncClient] = None,
    max_retries: int = 3,
) -> Dict[str, any]:
    """Index a single image via the API endpoint with retry logic."""
    import asyncio
    
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=600.0)  # 10 min timeout for large images
        close_client = True

    last_error = None
    try:
        for attempt in range(max_retries):
            try:
                with open(image_path, "rb") as f:
                    files = {
                        "image_file": (
                            image_path.name,
                            f,
                            "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
                        )
                    }
                    data = {
                        "image_type": image_type,
                        "store_in_kg": str(store_in_kg).lower(),
                    }

                    response = await client.post(INDEX_ENDPOINT, files=files, data=data, timeout=600.0)
                    response.raise_for_status()
                    return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                # Last attempt failed
                if isinstance(e, httpx.HTTPStatusError):
                    if e.response.status_code == 500:
                        raise Exception(f"Server error after {max_retries} attempts: {e.response.text[:200]}")
                    raise Exception(f"HTTP {e.response.status_code} after {max_retries} attempts: {e.response.text[:200]}")
                else:
                    raise Exception(f"Request error after {max_retries} attempts: {str(e)[:200]}")
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise
    finally:
        if close_client:
            await client.aclose()


async def ingest_batch(
    batch_images: List[Path],
    batch_name: str,
    image_type: str = "output",
    store_in_kg: bool = True,
    max_concurrent: int = 5,
) -> Dict[str, any]:
    """Ingest a batch of images to Qdrant."""
    results = {
        "total": len(batch_images),
        "success": 0,
        "failed": 0,
        "results": [],
    }

    if not batch_images:
        return results

    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_one(image_path: Path):
        async with semaphore:
            try:
                async with httpx.AsyncClient(timeout=600.0) as client:  # 10 min timeout
                    result = await index_image(image_path, image_type, store_in_kg, client)
                    return {"success": True, "path": str(image_path), "result": result}
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200] if hasattr(e.response, 'text') else 'No response text'}"
                return {"success": False, "path": str(image_path), "error": error_msg}
            except httpx.RequestError as e:
                return {"success": False, "path": str(image_path), "error": f"Request error: {str(e)[:100]}"}
            except Exception as e:
                return {"success": False, "path": str(image_path), "error": str(e)[:200]}

    # Process all images with progress bar
    tasks = [process_one(path) for path in batch_images]
    with tqdm(total=len(tasks), desc=f"  {batch_name}", unit="img", ncols=100, leave=False) as pbar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results["results"].append(result)

            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
                if results["failed"] <= 3:  # Only show first few errors
                    console.print(f"[red]✗ Failed: {Path(result['path']).name} - {result.get('error', 'Unknown')[:80]}[/red]")

            pbar.update(1)

    return results


async def check_api_health() -> tuple[bool, Optional[Dict[str, any]]]:
    """Check if the API server is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            # Just try the base URL - if we get ANY response, server is up
            try:
                response = await client.get(f"{API_BASE_URL}/", timeout=5.0)
                return True, None  # Any response means server is up
            except (httpx.ConnectError, httpx.TimeoutException):
                return False, {"error": "Could not connect to API server"}
            except Exception:
                return True, None  # Other errors might mean server is up but endpoint doesn't exist
    except Exception:
        return True, None  # Assume it's running, let the actual calls fail if not


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ingest images from uploads directory to Qdrant"
    )
    parser.add_argument(
        "--uploads-dir",
        default="uploads",
        help="Directory containing batched images (default: uploads)",
    )
    parser.add_argument(
        "--image-type",
        default="output",
        choices=["input", "output"],
        help="Image type to use (default: output)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=8,
        help="Max concurrent API calls per batch (default: 8, recommended: 5-10)",
    )
    parser.add_argument(
        "--store-in-kg",
        action="store_true",
        default=True,
        help="Store images in Knowledge Graph (default: True)",
    )
    parser.add_argument(
        "--no-store-in-kg",
        action="store_true",
        help="Don't store images in Knowledge Graph",
    )
    parser.add_argument(
        "--batch-start",
        type=int,
        default=None,
        help="Start processing from this batch index (0-based, for parallel processing)",
    )
    parser.add_argument(
        "--batch-end",
        type=int,
        default=None,
        help="Stop processing at this batch index (exclusive, for parallel processing)",
    )
    parser.add_argument(
        "--batch-names",
        nargs="*",
        default=None,
        help="Process only these specific batch names (e.g., batch_01 batch_02)",
    )

    args = parser.parse_args()
    
    store_in_kg = args.store_in_kg and not args.no_store_in_kg

    console.print(Panel.fit(
        "[bold cyan]Ingest Uploads Directory to Qdrant[/bold cyan]\n"
        "Processes batched images from uploads/ directory",
        border_style="cyan"
    ))

    # Skip health check - just try to connect
    console.print("\n[cyan]Connecting to API server...[/cyan]")
    console.print("[green]✓ Proceeding with ingestion[/green]")

    # Find images
    uploads_dir = Path(args.uploads_dir)
    console.print(f"\n[cyan]Scanning {uploads_dir} for images...[/cyan]")
    
    batches = find_images_in_uploads(uploads_dir)
    
    if not batches:
        console.print(f"[yellow]⚠️  No images found in {uploads_dir}[/yellow]")
        return 1

    # Filter batches if specified
    if args.batch_names:
        # Filter to only specified batch names
        filtered_batches = {name: batches[name] for name in args.batch_names if name in batches}
        if not filtered_batches:
            console.print(f"[red]✗ None of the specified batch names found: {args.batch_names}[/red]")
            return 1
        batches = filtered_batches
        console.print(f"[cyan]Filtered to {len(batches)} specified batches[/cyan]")
    elif args.batch_start is not None or args.batch_end is not None:
        # Filter by index range
        batch_list = sorted(batches.items())
        start_idx = args.batch_start if args.batch_start is not None else 0
        end_idx = args.batch_end if args.batch_end is not None else len(batch_list)
        filtered_batches = dict(batch_list[start_idx:end_idx])
        if not filtered_batches:
            console.print(f"[red]✗ No batches in range [{start_idx}:{end_idx}][/red]")
            return 1
        batches = filtered_batches
        console.print(f"[cyan]Processing batches {start_idx} to {end_idx-1} (inclusive)[/cyan]")

    total_images = sum(len(imgs) for imgs in batches.values())
    console.print(f"[green]✓ Found {total_images} images in {len(batches)} batches[/green]")

    # Ingest batches
    console.print(f"\n[bold cyan]🚀 Ingesting batches to Qdrant...[/bold cyan]")
    console.print(f"[cyan]Image type: {args.image_type}, Store in KG: {store_in_kg}[/cyan]\n")

    total_ingested = 0
    total_failed = 0

    for batch_name, batch_images in tqdm(batches.items(), desc="Processing batches", unit="batch", ncols=100):
        results = await ingest_batch(
            batch_images,
            batch_name,
            image_type=args.image_type,
            store_in_kg=store_in_kg,
            max_concurrent=args.max_concurrent,
        )

        total_ingested += results["success"]
        total_failed += results["failed"]

        if results["failed"] > 0:
            console.print(f"[yellow]⚠️  {batch_name}: {results['success']} success, {results['failed']} failed[/yellow]")
        else:
            console.print(f"[green]✓ {batch_name}: {results['success']} images ingested[/green]")

    # Final summary
    console.print("\n" + "="*80)
    console.print("[bold green]INGESTION COMPLETE[/bold green]")
    console.print("="*80)

    summary_table = Table(show_header=True, header_style="bold cyan")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total images", str(total_images))
    summary_table.add_row("Successfully ingested", str(total_ingested))
    summary_table.add_row("Failed", str(total_failed))
    summary_table.add_row("Success rate", f"{(total_ingested/total_images*100):.1f}%" if total_images > 0 else "0%")

    console.print(summary_table)

    # Check Qdrant
    try:
        from qdrant_client import QdrantClient
        c = QdrantClient(host="localhost", port=6333)
        info = c.get_collection("childrens_book_images")
        console.print(f"\n[green]✓ Qdrant now has {info.points_count} total points[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not verify Qdrant: {e}[/yellow]")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠️  Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)

