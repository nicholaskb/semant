#!/usr/bin/env python3
"""
Diagnostic script to check GCS bucket contents and Qdrant status.

This script will:
1. List what's actually in your GCS bucket
2. Check Qdrant for existing images
3. Show you how to ingest images if they exist
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import storage
from qdrant_client import QdrantClient
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def list_gcs_bucket_contents(bucket_name: str, prefix: str = "") -> List[Dict[str, Any]]:
    """List all files in a GCS bucket with optional prefix."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        blobs = list(bucket.list_blobs(prefix=prefix))
        
        results = []
        for blob in blobs:
            results.append({
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "updated": blob.updated.isoformat() if blob.updated else None,
            })
        
        return results
    except Exception as e:
        logger.error(f"Failed to list GCS bucket: {e}")
        return []


def check_qdrant_status(collection_name: str = "childrens_book_images") -> Dict[str, Any]:
    """Check Qdrant collection status."""
    try:
        client = QdrantClient(host="localhost", port=6333)
        
        # Get collection info
        try:
            collection_info = client.get_collection(collection_name)
            points_count = collection_info.points_count
        except Exception:
            points_count = 0
        
        # Sample some points to check for GCS URLs
        sample_points = []
        gcs_url_count = 0
        
        if points_count > 0:
            try:
                points, _ = client.scroll(
                    collection_name=collection_name,
                    limit=10,
                    with_payload=True
                )
                
                for point in points:
                    payload = point.payload
                    has_gcs = "gcs_url" in payload and payload.get("gcs_url")
                    if has_gcs:
                        gcs_url_count += 1
                    
                    sample_points.append({
                        "image_uri": payload.get("image_uri", "N/A")[:50],
                        "has_gcs_url": has_gcs,
                        "gcs_url": payload.get("gcs_url", "")[:60] if has_gcs else "N/A",
                    })
            except Exception as e:
                logger.warning(f"Failed to sample Qdrant points: {e}")
        
        return {
            "connected": True,
            "collection_exists": points_count > 0 or collection_info is not None,
            "points_count": points_count,
            "sample_points": sample_points,
            "gcs_url_count": gcs_url_count,
        }
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        return {
            "connected": False,
            "error": str(e),
        }


def find_image_paths(bucket_contents: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Find common image paths in bucket."""
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    
    paths_by_prefix = {}
    
    for item in bucket_contents:
        name = item["name"]
        
        # Check if it's an image
        if any(name.lower().endswith(ext) for ext in image_extensions):
            # Extract prefix (folder path)
            parts = name.split("/")
            if len(parts) > 1:
                prefix = "/".join(parts[:-1]) + "/"
            else:
                prefix = ""  # Root level
            
            if prefix not in paths_by_prefix:
                paths_by_prefix[prefix] = []
            paths_by_prefix[prefix].append(name)
    
    return paths_by_prefix


async def main():
    console.print(Panel.fit(
        "[bold cyan]GCS & Qdrant Diagnostic Tool[/bold cyan]",
        border_style="cyan"
    ))
    
    # Check Qdrant
    console.print("\n[bold cyan]1. Checking Qdrant Status...[/bold cyan]")
    qdrant_status = check_qdrant_status()
    
    if qdrant_status.get("connected"):
        console.print("[green]✓ Connected to Qdrant[/green]")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Collection exists", "Yes" if qdrant_status.get("collection_exists") else "No")
        table.add_row("Total points", str(qdrant_status.get("points_count", 0)))
        table.add_row("Points with GCS URL", str(qdrant_status.get("gcs_url_count", 0)))
        
        console.print(table)
        
        # Show sample points
        if qdrant_status.get("sample_points"):
            console.print("\n[bold cyan]Sample Points:[/bold cyan]")
            sample_table = Table(show_header=True, header_style="bold cyan")
            sample_table.add_column("Image URI", style="cyan", max_width=50)
            sample_table.add_column("Has GCS URL", style="yellow")
            sample_table.add_column("GCS URL", style="blue", max_width=60)
            
            for point in qdrant_status["sample_points"][:5]:
                sample_table.add_row(
                    point["image_uri"],
                    "✅" if point["has_gcs_url"] else "❌",
                    point["gcs_url"]
                )
            
            console.print(sample_table)
    else:
        console.print(f"[red]✗ Failed to connect to Qdrant: {qdrant_status.get('error', 'Unknown error')}[/red]")
        console.print("[yellow]Make sure Qdrant is running: docker run -d -p 6333:6333 qdrant/qdrant:latest[/yellow]")
    
    # Check GCS bucket
    console.print("\n[bold cyan]2. Checking GCS Bucket Contents...[/bold cyan]")
    bucket_name = "bahroo_public"  # Default bucket
    
    # Try to get from env or use default
    import os
    bucket_name = os.getenv("GCS_BUCKET_NAME", bucket_name)
    
    console.print(f"[cyan]Bucket:[/cyan] {bucket_name}")
    
    # List root level
    root_contents = list_gcs_bucket_contents(bucket_name, "")
    console.print(f"[green]✓ Found {len(root_contents)} total items in bucket[/green]")
    
    # Find image paths
    image_paths = find_image_paths(root_contents)
    
    if image_paths:
        console.print("\n[bold cyan]Image Paths Found:[/bold cyan]")
        path_table = Table(show_header=True, header_style="bold cyan")
        path_table.add_column("Prefix/Folder", style="cyan")
        path_table.add_column("Image Count", style="green")
        path_table.add_column("Sample Files", style="blue", max_width=60)
        
        for prefix, files in sorted(image_paths.items()):
            prefix_display = prefix if prefix else "(root)"
            sample = ", ".join([f.split("/")[-1] for f in files[:3]])
            if len(files) > 3:
                sample += f" ... (+{len(files) - 3} more)"
            
            path_table.add_row(
                prefix_display,
                str(len(files)),
                sample
            )
        
        console.print(path_table)
        
        # Check expected paths
        console.print("\n[bold cyan]3. Expected vs Actual Paths:[/bold cyan]")
        expected_paths = {
            "input_kids_monster/": "Input images",
            "generated_images/": "Output images",
        }
        
        expected_table = Table(show_header=True, header_style="bold cyan")
        expected_table.add_column("Expected Path", style="cyan")
        expected_table.add_column("Status", style="yellow")
        expected_table.add_column("Found Images", style="green")
        
        for expected_path, description in expected_paths.items():
            found_count = len(image_paths.get(expected_path, []))
            if found_count > 0:
                status = f"✅ Found ({found_count} images)"
            else:
                status = "❌ Not found"
            
            expected_table.add_row(
                expected_path,
                status,
                str(found_count)
            )
        
        console.print(expected_table)
        
        # Suggest ingestion command
        console.print("\n[bold cyan]4. How to Ingest Images:[/bold cyan]")
        
        # Find best prefix to use
        if image_paths.get("input_kids_monster/"):
            input_prefix = "input_kids_monster/"
        elif any("input" in p.lower() for p in image_paths.keys()):
            input_prefix = [p for p in image_paths.keys() if "input" in p.lower()][0]
        else:
            input_prefix = list(image_paths.keys())[0] if image_paths else ""
        
        if image_paths.get("generated_images/"):
            output_prefix = "generated_images/"
        elif any("output" in p.lower() or "generated" in p.lower() for p in image_paths.keys()):
            output_prefix = [p for p in image_paths.keys() if "output" in p.lower() or "generated" in p.lower()][0]
        else:
            output_prefix = list(image_paths.keys())[1] if len(image_paths) > 1 else ""
        
        if input_prefix or output_prefix:
            console.print("\n[bold green]Suggested ingestion command:[/bold green]")
            cmd_parts = ["python scripts/generate_childrens_book.py"]
            cmd_parts.append(f"--bucket {bucket_name}")
            
            if input_prefix:
                cmd_parts.append(f'--input-prefix "{input_prefix}"')
            if output_prefix:
                cmd_parts.append(f'--output-prefix "{output_prefix}"')
            
            console.print(f"[cyan]{' '.join(cmd_parts)}[/cyan]")
        else:
            console.print("[yellow]⚠️  No clear input/output paths found. You may need to organize your bucket first.[/yellow]")
    else:
        console.print("[yellow]⚠️  No images found in bucket[/yellow]")
        console.print("\n[bold cyan]To add images:[/bold cyan]")
        console.print("1. Upload images to GCS:")
        console.print(f"   [cyan]gsutil -m cp -r local_images/input/ gs://{bucket_name}/input_kids_monster/[/cyan]")
        console.print(f"   [cyan]gsutil -m cp -r local_images/output/ gs://{bucket_name}/generated_images/[/cyan]")
        console.print("\n2. Then run ingestion:")
        console.print(f"   [cyan]python scripts/generate_childrens_book.py --bucket {bucket_name}[/cyan]")


if __name__ == "__main__":
    asyncio.run(main())

