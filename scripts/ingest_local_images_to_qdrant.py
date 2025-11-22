#!/usr/bin/env python3
"""
Ingest local images into Qdrant via the /api/images/index endpoint.

This script:
1. Finds all images in generated_books/ directories
2. Determines image type (input/output) from directory structure
3. Uploads each image via the API endpoint
4. Stores embeddings in Qdrant + optionally in KG
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import httpx
from dotenv import load_dotenv
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import time

# Load environment variables from .env file
load_dotenv()

console = Console()

# API endpoint - can be overridden via .env
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
INDEX_ENDPOINT = f"{API_BASE_URL}/api/images/index"

# Image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def find_local_images(base_dir: Path = Path("generated_books")) -> Dict[str, List[Path]]:
    """
    Find all images in generated_books directories, organized by type.
    
    Returns:
        {
            "input": [list of input image paths],
            "output": [list of output image paths]
        }
    """
    images = {"input": [], "output": []}
    
    if not base_dir.exists():
        console.print(f"[yellow]⚠️  Directory {base_dir} does not exist[/yellow]")
        return images
    
    # Find all image files
    for image_path in base_dir.rglob("*"):
        if image_path.is_file() and image_path.suffix.lower() in IMAGE_EXTENSIONS:
            # Determine type from path
            parts = image_path.parts
            if "input" in parts:
                images["input"].append(image_path)
            elif "output" in parts:
                images["output"].append(image_path)
            else:
                # Default to output if unclear
                images["output"].append(image_path)
    
    return images


async def index_image(
    image_path: Path,
    image_type: str,
    store_in_kg: bool = True,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """
    Index a single image via the API endpoint.
    
    Args:
        image_path: Path to the image file
        image_type: "input" or "output"
        store_in_kg: Whether to also store in Knowledge Graph
        client: HTTP client (will create if not provided)
    
    Returns:
        Response dict from API
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout for large images
        close_client = True
    
    try:
        with open(image_path, "rb") as f:
            files = {"image_file": (image_path.name, f, "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png")}
            data = {
                "image_type": image_type,
                "store_in_kg": str(store_in_kg).lower(),
            }
            
            response = await client.post(INDEX_ENDPOINT, files=files, data=data)
            response.raise_for_status()
            return response.json()
    finally:
        if close_client:
            await client.aclose()


async def ingest_all_images(
    images: Dict[str, List[Path]],
    store_in_kg: bool = True,
    max_concurrent: int = 5,
) -> Dict[str, Any]:
    """
    Ingest all images with progress tracking.
    
    Args:
        images: Dict with "input" and "output" lists of image paths
        store_in_kg: Whether to store in KG
        max_concurrent: Max concurrent uploads
    
    Returns:
        Results summary
    """
    all_images = []
    for img_type, paths in images.items():
        for path in paths:
            all_images.append((path, img_type))
    
    total = len(all_images)
    if total == 0:
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "results": [],
        }
    
    console.print(f"\n[bold cyan]Found {total} images to ingest[/bold cyan]")
    console.print(f"  Input: {len(images['input'])}")
    console.print(f"  Output: {len(images['output'])}")
    
    results = {
        "total": total,
        "success": 0,
        "failed": 0,
        "results": [],
    }
    
    # Create HTTP client for reuse
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Process in batches to limit concurrency and memory usage
        semaphore = asyncio.Semaphore(max_concurrent)
        batch_size = 50  # Process 50 images at a time
        
        async def process_one(image_path: Path, img_type: str):
            async with semaphore:
                try:
                    result = await index_image(image_path, img_type, store_in_kg, client)
                    return {"success": True, "path": str(image_path), "result": result}
                except httpx.HTTPStatusError as e:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:100]}"
                    return {"success": False, "path": str(image_path), "error": error_msg}
                except httpx.RequestError as e:
                    return {"success": False, "path": str(image_path), "error": f"Request error: {str(e)[:100]}"}
                except Exception as e:
                    return {"success": False, "path": str(image_path), "error": str(e)[:200]}
        
        # Process all images with progress bar using tqdm
        with tqdm(total=total, desc="Ingesting images", unit="img", ncols=100) as pbar:
            # Process in batches to avoid overwhelming the system
            for batch_start in range(0, total, batch_size):
                batch_end = min(batch_start + batch_size, total)
                batch_images = all_images[batch_start:batch_end]
                
                # Create tasks for this batch only
                batch_tasks = [process_one(path, img_type) for path, img_type in batch_images]
                
                # Process batch results as they complete
                for coro in asyncio.as_completed(batch_tasks):
                    result = await coro
                    results["results"].append(result)
                    
                    if result["success"]:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        # Only print first few errors to avoid spam
                        if results["failed"] <= 5:
                            console.print(f"[red]✗ Failed: {Path(result['path']).name}[/red]")
                            console.print(f"   Error: {result['error'][:100]}")
                    
                    pbar.update(1)
                
                # Small delay between batches to avoid overwhelming the API
                if batch_end < total:
                    await asyncio.sleep(0.5)
    
    return results


async def check_api_health() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if the API server is running and get Qdrant config."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Try multiple endpoints to verify server is running
            endpoints_to_try = [
                f"{API_BASE_URL}/api/health",
                f"{API_BASE_URL}/health", 
                f"{API_BASE_URL}/",
                f"{API_BASE_URL}/docs"  # FastAPI docs endpoint
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    response = await client.get(endpoint)
                    # If we get any response (even 404), server is running
                    if response.status_code in [200, 404]:
                        return True, None
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    # Connection errors mean server is not running
                    continue
                except Exception:
                    # Other errors, try next endpoint
                    continue
            
            # If we get here, couldn't connect to any endpoint
            return False, {"error": "Could not connect to API server"}
    except Exception as e:
        return False, {"error": str(e)}


def check_qdrant_config() -> Dict[str, str]:
    """Check Qdrant configuration from environment."""
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = os.getenv("QDRANT_PORT", "6333")
    collection_name = os.getenv("QDRANT_COLLECTION", "childrens_book_images")
    
    return {
        "host": qdrant_host,
        "port": qdrant_port,
        "collection": collection_name,
        "url": f"{qdrant_host}:{qdrant_port}",
    }


async def main():
    console.print(Panel.fit(
        "[bold cyan]Local Image Ingestion to Qdrant[/bold cyan]\n"
        "Uploads local images via /api/images/index endpoint",
        border_style="cyan"
    ))
    
    # Skip health check - just proceed
    console.print("\n[cyan]Connecting to API server...[/cyan]")
    console.print("[green]✓ Proceeding with ingestion[/green]")
    
    # Check Qdrant configuration
    console.print("\n[cyan]Checking Qdrant configuration...[/cyan]")
    qdrant_config = check_qdrant_config()
    
    config_table = Table(show_header=True, header_style="bold cyan")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    
    config_table.add_row("Qdrant Host", qdrant_config["host"])
    config_table.add_row("Qdrant Port", qdrant_config["port"])
    config_table.add_row("Collection Name", qdrant_config["collection"])
    config_table.add_row("Connection URL", qdrant_config["url"])
    
    console.print(config_table)
    
    # Verify Qdrant is accessible
    try:
        from qdrant_client import QdrantClient
        test_client = QdrantClient(host=qdrant_config["host"], port=int(qdrant_config["port"]))
        # Try to get collections to verify connection
        collections = test_client.get_collections()
        console.print(f"[green]✓ Qdrant is accessible at {qdrant_config['url']}[/green]")
        
        # Check if collection exists
        collection_exists = any(c.name == qdrant_config["collection"] for c in collections.collections)
        if collection_exists:
            collection_info = test_client.get_collection(qdrant_config["collection"])
            console.print(f"[green]✓ Collection '{qdrant_config['collection']}' exists ({collection_info.points_count} points)[/green]")
        else:
            console.print(f"[yellow]⚠️  Collection '{qdrant_config['collection']}' will be created[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Cannot connect to Qdrant at {qdrant_config['url']}[/red]")
        console.print(f"   Error: {e}")
        console.print("\n[bold yellow]Please start Qdrant:[/bold yellow]")
        console.print("[cyan]  docker run -d -p 6333:6333 qdrant/qdrant:latest[/cyan]")
        console.print("\nOr if using different host/port, set in .env:")
        console.print("[cyan]  QDRANT_HOST=your-host[/cyan]")
        console.print("[cyan]  QDRANT_PORT=your-port[/cyan]")
        
        # Ask if user wants to continue anyway
        console.print("\n[yellow]⚠️  Continuing anyway - API will handle Qdrant connection[/yellow]")
    
    # Find images
    console.print("\n[cyan]Scanning for local images...[/cyan]")
    images = find_local_images()
    
    total_images = len(images["input"]) + len(images["output"])
    
    if total_images == 0:
        console.print("[yellow]⚠️  No images found in generated_books/ directories[/yellow]")
        console.print("\n[cyan]Looking for images in:[/cyan]")
        console.print("  - generated_books/*/input/")
        console.print("  - generated_books/*/output/")
        sys.exit(0)
    
    # Show summary
    console.print(f"\n[green]✓ Found {total_images} images[/green]")
    
    # Check if store_in_kg should be enabled (default True, can override via env)
    store_in_kg = os.getenv("STORE_IN_KG", "true").lower() == "true"
    
    # Ingest images
    start_time = time.time()
    results = await ingest_all_images(images, store_in_kg=store_in_kg, max_concurrent=5)
    elapsed = time.time() - start_time
    
    # Show results
    console.print("\n" + "="*70)
    console.print("[bold]Ingestion Results[/bold]")
    console.print("="*70)
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total images", str(results["total"]))
    table.add_row("Successfully ingested", str(results["success"]))
    table.add_row("Failed", str(results["failed"]))
    table.add_row("Time elapsed", f"{elapsed:.1f}s")
    
    if results["success"] > 0:
        avg_time = elapsed / results["success"]
        table.add_row("Avg time per image", f"{avg_time:.2f}s")
    
    console.print(table)
    
    # Show sample successful results
    successful = [r for r in results["results"] if r["success"]]
    if successful:
        console.print("\n[bold cyan]Sample Successful Ingestion:[/bold cyan]")
        sample_table = Table(show_header=True, header_style="bold cyan")
        sample_table.add_column("Image", style="cyan", max_width=50)
        sample_table.add_column("Image URI", style="blue", max_width=50)
        sample_table.add_column("GCS URL", style="green", max_width=40)
        
        for result in successful[:5]:
            res_data = result.get("result", {})
            image_uri = res_data.get("image_uri", "N/A")
            gcs_url = res_data.get("gcs_url", "N/A")
            if isinstance(gcs_url, dict):
                gcs_url = gcs_url.get("gcs_url", "N/A")
            
            # Truncate paths
            path = Path(result["path"])
            path_display = "/".join(path.parts[-3:])  # Last 3 parts
            
            sample_table.add_row(
                path_display,
                image_uri[:50] if len(image_uri) > 50 else image_uri,
                gcs_url[:40] if isinstance(gcs_url, str) and len(gcs_url) > 40 else str(gcs_url)[:40]
            )
        
        console.print(sample_table)
    
    # Final status
    console.print("\n" + "="*70)
    if results["success"] == results["total"]:
        console.print("[bold green]✅ All images successfully ingested![/bold green]")
        console.print(f"\n[cyan]You can now verify in Qdrant:[/cyan]")
        console.print("[cyan]  python scripts/verify_backfill_kg.py[/cyan]")
    elif results["success"] > 0:
        console.print(f"[bold yellow]⚠️  Partially successful: {results['success']}/{results['total']} images ingested[/bold yellow]")
    else:
        console.print("[bold red]❌ All images failed to ingest[/bold red]")
        console.print("\n[cyan]Check the errors above and ensure:[/cyan]")
        console.print("  1. API server is running")
        console.print("  2. Qdrant is running (docker run -d -p 6333:6333 qdrant/qdrant:latest)")
        console.print("  3. GCS_BUCKET_NAME is set in environment")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)

