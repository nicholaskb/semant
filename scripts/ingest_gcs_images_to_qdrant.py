#!/usr/bin/env python3
"""
Download images from GCS, batch them, ingest to Qdrant, and clean up temp files.

This script:
1. Downloads images from GCS using parallel downloads (fast)
2. Splits input/output images into manageable batches
3. Ingests each batch to Qdrant via /api/images/index
4. Uses tqdm for progress tracking
5. Cleans up all temp files after successful ingestion

Requirements:
- Python 3.8+
- pip install google-cloud-storage python-dotenv httpx tqdm rich

Setup:
1. Set GCS_BUCKET_NAME environment variable
2. Set up Google Cloud credentials (gcloud auth application-default login)
   OR set GOOGLE_APPLICATION_CREDENTIALS to your service account key file
3. Ensure API server is running (python main.py)
4. Ensure Qdrant is running (docker run -d -p 6333:6333 qdrant/qdrant:latest)

Usage:
    python scripts/ingest_gcs_images_to_qdrant.py
    python scripts/ingest_gcs_images_to_qdrant.py --batch-size 50
    python scripts/ingest_gcs_images_to_qdrant.py --input-only
    python scripts/ingest_gcs_images_to_qdrant.py --output-only
    python scripts/ingest_gcs_images_to_qdrant.py --max-concurrent 10
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import httpx
from dotenv import load_dotenv
from google.cloud import storage
from google.cloud.exceptions import NotFound
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from tqdm import tqdm

# Load environment variables
load_dotenv()

console = Console()

# API endpoint - can be overridden via .env
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
INDEX_ENDPOINT = f"{API_BASE_URL}/api/images/index"

# Image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def log(message: str) -> None:
    """Log a message."""
    console.print(message)


def ensure_directory(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def iter_blob_names(
    bucket: storage.Bucket,
    prefix: str,
    extensions: Optional[Tuple[str, ...]] = None,
) -> List[str]:
    """List all blob names matching prefix and extensions."""
    normalized_extensions = None
    if extensions:
        normalized_extensions = tuple(ext.lower().lstrip('.') for ext in extensions)

    blob_names = []
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith('/'):
            continue
        if normalized_extensions:
            suffix = Path(blob.name).suffix.lower().lstrip('.')
            if suffix not in normalized_extensions:
                continue
        blob_names.append(blob.name)

    return blob_names


def download_file_fast(
    bucket: storage.Bucket,
    blob_name: str,
    destination_dir: Path,
    overwrite: bool = False,
) -> Tuple[bool, Optional[Tuple[str, str]]]:
    """Download a single file from GCS (fast, parallel-ready).
    
    Returns:
        Tuple of (success, (local_path, original_blob_name)) or (False, None)
    """
    destination = destination_dir / Path(blob_name).name

    if destination.exists() and not overwrite:
        return False, None  # Skipped

    blob = bucket.blob(blob_name)

    try:
        blob.download_to_filename(str(destination))
        return True, (str(destination), blob_name)  # Return both path and original blob name
    except NotFound:
        return False, None
    except Exception as exc:
        log(f"❌ Failed to download {blob_name}: {exc}")
        return False, None


def download_batch_parallel(
    bucket: storage.Bucket,
    blob_names: List[str],
    destination_dir: Path,
    max_workers: int = 20,
    overwrite: bool = False,
) -> Tuple[int, int, int, Dict[str, str]]:
    """Download multiple files in parallel using ThreadPoolExecutor.
    
    Returns:
        Tuple of (downloaded_count, skipped_count, failed_count, blob_mapping)
        where blob_mapping maps local filename -> original GCS blob name
    """
    ensure_directory(destination_dir)
    
    blob_mapping: Dict[str, str] = {}  # local_filename -> original_blob_name

    downloaded = 0
    skipped = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download tasks
        future_to_blob = {
            executor.submit(download_file_fast, bucket, blob_name, destination_dir, overwrite): blob_name
            for blob_name in blob_names
        }

        # Process completed downloads with progress bar
        with tqdm(total=len(blob_names), desc="Downloading", unit="file", ncols=100) as pbar:
            for future in as_completed(future_to_blob):
                blob_name = future_to_blob[future]
                try:
                    success, result = future.result()
                    if success and result:
                        local_path, original_blob = result
                        local_filename = Path(local_path).name
                        blob_mapping[local_filename] = original_blob
                        downloaded += 1
                    else:
                        skipped += 1
                except Exception as e:
                    log(f"❌ Error downloading {blob_name}: {e}")
                    failed += 1
                finally:
                    pbar.update(1)

    return downloaded, skipped, failed, blob_mapping


def split_into_batches(
    image_paths: List[Path],
    batch_size: int,
    batch_type: str,
) -> Dict[str, List[Path]]:
    """Split image paths into batches."""
    batches = {}
    num_batches = (len(image_paths) + batch_size - 1) // batch_size

    for batch_num in range(1, num_batches + 1):
        batch_name = f"{batch_type}_batch_{batch_num:02d}"
        start_idx = (batch_num - 1) * batch_size
        end_idx = min(batch_num * batch_size, len(image_paths))
        batches[batch_name] = image_paths[start_idx:end_idx]

    return batches


async def index_image(
    image_path: Path,
    image_type: str,
    original_gcs_blob: Optional[str] = None,
    bucket_name: Optional[str] = None,
    store_in_kg: bool = True,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """Index a single image via the API endpoint.
    
    Args:
        image_path: Local path to the image file
        image_type: Type of image (input/output)
        original_gcs_blob: Original GCS blob name (e.g., "input_kids_monster/image.png")
        bucket_name: GCS bucket name (required if original_gcs_blob is provided)
        store_in_kg: Whether to store in Knowledge Graph
        client: Optional HTTP client (creates new one if None)
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout
        close_client = True

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
            
            # If we have the original GCS blob path, pass it via metadata_json
            # This ensures Qdrant stores the original GCS URL, not the new indexed/ path
            if original_gcs_blob and bucket_name:
                original_gcs_url = f"gs://{bucket_name}/{original_gcs_blob}"
                metadata_override = {
                    "gcs_url": original_gcs_url,
                    "original_blob": original_gcs_blob,
                }
                data["metadata_json"] = json.dumps(metadata_override)

            response = await client.post(INDEX_ENDPOINT, files=files, data=data)
            response.raise_for_status()
            return response.json()
    finally:
        if close_client:
            await client.aclose()


async def ingest_batch(
    batch_images: List[Tuple[Path, Optional[str]]],
    image_type: str,
    bucket_name: Optional[str] = None,
    store_in_kg: bool = True,
    max_concurrent: int = 5,
) -> Dict[str, Any]:
    """Ingest a batch of images to Qdrant.
    
    Args:
        batch_images: List of tuples (image_path, original_gcs_blob_name)
        image_type: Type of image (input/output)
        bucket_name: GCS bucket name (required to construct gcs_url)
        store_in_kg: Whether to store in Knowledge Graph
        max_concurrent: Max concurrent API calls
    """
    results = {
        "total": len(batch_images),
        "success": 0,
        "failed": 0,
        "results": [],
    }

    if not batch_images:
        return results

    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_one(image_tuple: Tuple[Path, Optional[str]]):
        image_path, original_blob = image_tuple
        async with semaphore:
            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    result = await index_image(
                        image_path, 
                        image_type, 
                        original_gcs_blob=original_blob,
                        bucket_name=bucket_name,
                        store_in_kg=store_in_kg, 
                        client=client
                    )
                    return {"success": True, "path": str(image_path), "result": result}
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text[:100]}"
                return {"success": False, "path": str(image_path), "error": error_msg}
            except httpx.RequestError as e:
                return {"success": False, "path": str(image_path), "error": f"Request error: {str(e)[:100]}"}
            except Exception as e:
                return {"success": False, "path": str(image_path), "error": str(e)[:200]}

    # Process all images with progress bar
    tasks = [process_one(img_tuple) for img_tuple in batch_images]
    with tqdm(total=len(tasks), desc=f"Ingesting {image_type}", unit="img", ncols=100, leave=False) as pbar:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results["results"].append(result)

            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
                if results["failed"] <= 3:  # Only show first few errors
                    log(f"[red]✗ Failed: {Path(result['path']).name}[/red]")

            pbar.update(1)

    return results


async def check_api_health() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if the API server is running."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            endpoints_to_try = [
                f"{API_BASE_URL}/api/health",
                f"{API_BASE_URL}/health",
                f"{API_BASE_URL}/",
                f"{API_BASE_URL}/docs"
            ]

            for endpoint in endpoints_to_try:
                try:
                    response = await client.get(endpoint)
                    if response.status_code in [200, 404]:
                        return True, None
                except (httpx.ConnectError, httpx.TimeoutException):
                    continue
                except Exception:
                    continue

            return False, {"error": "Could not connect to API server"}
    except Exception as e:
        return False, {"error": str(e)}


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download images from GCS, batch them, and ingest to Qdrant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download and ingest all images (default batch size: 50)
  python scripts/ingest_gcs_images_to_qdrant.py

  # Custom batch size
  python scripts/ingest_gcs_images_to_qdrant.py --batch-size 100

  # Download only input images
  python scripts/ingest_gcs_images_to_qdrant.py --input-only

  # Download only generated outputs
  python scripts/ingest_gcs_images_to_qdrant.py --output-only

  # More parallel downloads
  python scripts/ingest_gcs_images_to_qdrant.py --download-workers 30

  # More concurrent API calls
  python scripts/ingest_gcs_images_to_qdrant.py --max-concurrent 10
        """
    )

    # Bucket configuration
    default_bucket = os.getenv("GCS_BUCKET_NAME", "bahroo_public")
    parser.add_argument(
        "--bucket",
        default=default_bucket,
        help=f"GCS bucket name (default: {default_bucket})",
    )

    # What to download
    parser.add_argument(
        "--input-only",
        action="store_true",
        help="Download only input images",
    )
    parser.add_argument(
        "--output-only",
        action="store_true",
        help="Download only generated outputs",
    )

    # Input configuration
    parser.add_argument(
        "--input-prefix",
        default="input_kids_monster/",
        help="GCS prefix for input images (default: input_kids_monster/)",
    )
    parser.add_argument(
        "--output-prefix",
        default="generated_images/",
        help="GCS prefix for generated outputs (default: generated_images/)",
    )

    # Batch configuration
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of images per batch for ingestion (default: 50)",
    )

    # Parallelism
    parser.add_argument(
        "--download-workers",
        type=int,
        default=20,
        help="Number of parallel download workers (default: 20)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Max concurrent API calls per batch (default: 5)",
    )

    # Options
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=["png", "jpg", "jpeg", "gif", "webp"],
        help="File extensions to download (default: png jpg jpeg gif webp)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files that already exist locally",
    )
    parser.add_argument(
        "--store-in-kg",
        action="store_true",
        default=True,
        help="Store images in Knowledge Graph (default: True)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't clean up temp files after ingestion (for debugging)",
    )

    args = parser.parse_args()

    # Validate mutually exclusive options
    if args.input_only and args.output_only:
        parser.error("--input-only and --output-only are mutually exclusive")

    # Determine what to download
    download_inputs = not args.output_only
    download_outputs = not args.input_only

    console.print(Panel.fit(
        "[bold cyan]GCS Image Ingestion to Qdrant[/bold cyan]\n"
        "Downloads from GCS → Batches → Ingests to Qdrant → Cleans up",
        border_style="cyan"
    ))

    # Check API health
    console.print("\n[cyan]Checking API server...[/cyan]")
    api_running, health_data = await check_api_health()

    if not api_running:
        console.print("[red]✗ API server is not running![/red]")
        console.print("\n[bold yellow]Please start the API server first:[/bold yellow]")
        console.print("[cyan]  python main.py[/cyan]")
        console.print("\nOr if using uvicorn:")
        console.print("[cyan]  uvicorn main:app --host 0.0.0.0 --port 8000[/cyan]")
        return 1

    console.print("[green]✓ API server is running[/green]")

    # Check Google Cloud authentication
    console.print("\n[cyan]Checking GCS connection...[/cyan]")
    try:
        client = storage.Client()
        bucket = client.bucket(args.bucket)
        bucket.reload()
        console.print(f"[green]✓ Connected to GCS bucket: {args.bucket}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to connect to GCS: {e}[/red]")
        console.print("\n[bold yellow]Please ensure:[/bold yellow]")
        console.print("1. You have authenticated with Google Cloud:")
        console.print("   [cyan]gcloud auth application-default login[/cyan]")
        console.print("\n2. OR set GOOGLE_APPLICATION_CREDENTIALS:")
        console.print("   [cyan]export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json[/cyan]")
        return 1

    # Create temporary directory for downloads
    temp_dir = Path(tempfile.mkdtemp(prefix="qdrant_ingest_"))
    console.print(f"\n[cyan]Using temp directory: {temp_dir}[/cyan]")

    try:
        input_dir = temp_dir / "input"
        output_dir = temp_dir / "output"
        ensure_directory(input_dir)
        ensure_directory(output_dir)

        total_downloaded = 0
        total_skipped = 0
        total_failed = 0

        # Download input images
        input_blob_names = []
        input_blob_mapping: Dict[str, str] = {}
        if download_inputs:
            console.print(f"\n[bold cyan]📥 Downloading input images from {args.input_prefix}...[/bold cyan]")
            input_blob_names = iter_blob_names(bucket, args.input_prefix, tuple(args.extensions))
            console.print(f"[cyan]Found {len(input_blob_names)} input images[/cyan]")

            if input_blob_names:
                downloaded, skipped, failed, mapping = download_batch_parallel(
                    bucket,
                    input_blob_names,
                    input_dir,
                    max_workers=args.download_workers,
                    overwrite=args.overwrite,
                )
                input_blob_mapping.update(mapping)
                total_downloaded += downloaded
                total_skipped += skipped
                total_failed += failed
                console.print(f"[green]✓ Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}[/green]")

        # Download output images
        output_blob_names = []
        output_blob_mapping: Dict[str, str] = {}
        if download_outputs:
            console.print(f"\n[bold cyan]📥 Downloading output images from {args.output_prefix}...[/bold cyan]")
            output_blob_names = iter_blob_names(bucket, args.output_prefix, tuple(args.extensions))
            console.print(f"[cyan]Found {len(output_blob_names)} output images[/cyan]")

            if output_blob_names:
                downloaded, skipped, failed, mapping = download_batch_parallel(
                    bucket,
                    output_blob_names,
                    output_dir,
                    max_workers=args.download_workers,
                    overwrite=args.overwrite,
                )
                output_blob_mapping.update(mapping)
                total_downloaded += downloaded
                total_skipped += skipped
                total_failed += failed
                console.print(f"[green]✓ Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}[/green]")

        # Get all image paths with their original blob names
        input_images = []
        if download_inputs:
            for img_path in input_dir.glob("*"):
                if img_path.is_file() and img_path.suffix.lower() in IMAGE_EXTENSIONS:
                    original_blob = input_blob_mapping.get(img_path.name)
                    input_images.append((img_path, original_blob))

        output_images = []
        if download_outputs:
            for img_path in output_dir.glob("*"):
                if img_path.is_file() and img_path.suffix.lower() in IMAGE_EXTENSIONS:
                    original_blob = output_blob_mapping.get(img_path.name)
                    output_images.append((img_path, original_blob))

        total_images = len(input_images) + len(output_images)

        if total_images == 0:
            console.print("\n[yellow]⚠️  No images to ingest![/yellow]")
            return 0

        console.print(f"\n[bold cyan]📦 Splitting into batches (batch size: {args.batch_size})...[/bold cyan]")

        # Split into batches (now handling tuples of (path, blob_name))
        def split_tuples_into_batches(image_tuples: List[Tuple[Path, Optional[str]]], batch_size: int, batch_type: str) -> Dict[str, List[Tuple[Path, Optional[str]]]]:
            """Split image tuples into batches."""
            batches = {}
            num_batches = (len(image_tuples) + batch_size - 1) // batch_size

            for batch_num in range(1, num_batches + 1):
                batch_name = f"{batch_type}_batch_{batch_num:02d}"
                start_idx = (batch_num - 1) * batch_size
                end_idx = min(batch_num * batch_size, len(image_tuples))
                batches[batch_name] = image_tuples[start_idx:end_idx]

            return batches

        input_batches = split_tuples_into_batches(input_images, args.batch_size, "input") if input_images else {}
        output_batches = split_tuples_into_batches(output_images, args.batch_size, "output") if output_images else {}

        all_batches = {**input_batches, **output_batches}
        console.print(f"[cyan]Created {len(all_batches)} batches[/cyan]")

        # Ingest batches
        console.print(f"\n[bold cyan]🚀 Ingesting batches to Qdrant...[/bold cyan]")
        total_ingested = 0
        total_ingest_failed = 0

        for batch_name, batch_image_tuples in tqdm(all_batches.items(), desc="Processing batches", unit="batch", ncols=100):
            # Determine image type from batch name
            image_type = "input" if batch_name.startswith("input_") else "output"

            # Ingest batch (pass bucket name so we can construct gcs_url)
            results = await ingest_batch(
                batch_image_tuples,
                image_type,
                bucket_name=args.bucket,
                store_in_kg=args.store_in_kg,
                max_concurrent=args.max_concurrent,
            )

            total_ingested += results["success"]
            total_ingest_failed += results["failed"]

            # Clean up batch files after successful ingestion
            if not args.no_cleanup:
                for img_tuple in batch_image_tuples:
                    img_path, _ = img_tuple
                    try:
                        img_path.unlink(missing_ok=True)
                    except Exception:
                        pass

        console.print(f"\n[green]✓ Ingestion complete![/green]")
        console.print(f"   Successfully ingested: {total_ingested}")
        console.print(f"   Failed: {total_ingest_failed}")

        # Final summary
        console.print("\n" + "="*80)
        console.print("[bold green]INGESTION COMPLETE[/bold green]")
        console.print("="*80)

        summary_table = Table(show_header=True, header_style="bold cyan")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Images downloaded", str(total_downloaded))
        summary_table.add_row("Images skipped", str(total_skipped))
        summary_table.add_row("Downloads failed", str(total_failed))
        summary_table.add_row("Images ingested", str(total_ingested))
        summary_table.add_row("Ingestions failed", str(total_ingest_failed))

        console.print(summary_table)

        return 0 if total_ingest_failed == 0 else 1

    finally:
        # Clean up temp directory
        if not args.no_cleanup and temp_dir.exists():
            console.print(f"\n[cyan]🧹 Cleaning up temp directory...[/cyan]")
            try:
                shutil.rmtree(temp_dir)
                console.print("[green]✓ Cleanup complete[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Cleanup warning: {e}[/yellow]")
        elif args.no_cleanup:
            console.print(f"\n[yellow]⚠️  Temp files preserved: {temp_dir}[/yellow]")


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

