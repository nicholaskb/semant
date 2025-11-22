#!/usr/bin/env python3
"""
Verification script for KG backfill from Qdrant.

This script verifies that:
1. Images from Qdrant have been properly backfilled into KG
2. KG nodes have schema:contentUrl pointing to GCS URLs
3. The API fallback mechanism can find images in KG when Qdrant metadata is missing
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

async def verify_backfill(
    collection_name: str = "childrens_book_images",
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
    sample_size: int = 10
) -> Dict[str, Any]:
    """
    Verify that KG backfill worked correctly.
    
    Returns:
        Verification results with statistics
    """
    console.print(Panel.fit(
        "[bold cyan]KG Backfill Verification[/bold cyan]",
        border_style="cyan"
    ))
    
    results = {
        "qdrant_images": 0,
        "kg_images": 0,
        "kg_with_gcs_url": 0,
        "qdrant_with_gcs_url": 0,
        "qdrant_missing_gcs_url": 0,
        "kg_can_fallback": 0,
        "sample_verification": []
    }
    
    # Connect to Qdrant
    try:
        qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        console.print("[green]✓ Connected to Qdrant[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to connect to Qdrant: {e}[/red]")
        return {"error": str(e)}
    
    # Connect to KG - use try/finally to ensure cleanup
    kg = None
    try:
        kg = KnowledgeGraphManager(persistent_storage=True)
        await kg.initialize()
        console.print("[green]✓ Connected to Knowledge Graph[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to connect to KG: {e}[/red]")
        return {"error": str(e)}
    
    try:
        # Get all points from Qdrant (with pagination)
        console.print(f"\n[bold cyan]📦 Fetching images from Qdrant collection '{collection_name}'...[/bold cyan]")
        try:
            all_points = []
            next_page_offset = None
            
            while True:
                points, next_page_offset = qdrant_client.scroll(
                    collection_name=collection_name,
                    limit=1000,  # Fetch in batches
                    offset=next_page_offset,
                    with_payload=True
                )
                
                if not points:
                    break
                    
                all_points.extend(points)
                console.print(f"  Fetched {len(points)} images (total: {len(all_points)})...")
                
                if next_page_offset is None:
                    break
            
            points = all_points
            results["qdrant_images"] = len(points)
            console.print(f"[green]✓ Found {len(points)} total images in Qdrant[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to fetch from Qdrant: {e}[/red]")
            return {"error": str(e)}
        
        if not points:
            console.print("[yellow]⚠️  No images found in Qdrant[/yellow]")
            return results
        
        # Count Qdrant images with/without gcs_url
        for point in points:
            gcs_url = point.payload.get("gcs_url", "")
            if gcs_url:
                results["qdrant_with_gcs_url"] += 1
            else:
                results["qdrant_missing_gcs_url"] += 1
        
        # Query KG for all ImageObject nodes
        console.print(f"\n[bold cyan]🔍 Querying Knowledge Graph for ImageObject nodes...[/bold cyan]")
        kg_query = """
        PREFIX schema: <http://schema.org/>
        SELECT ?image ?gcs_url WHERE {
            ?image a schema:ImageObject .
            OPTIONAL { ?image schema:contentUrl ?gcs_url . }
        }
        """
        
        try:
            kg_results = await kg.query_graph(kg_query)
            results["kg_images"] = len(kg_results) if kg_results else 0
            
            # Count how many have GCS URLs
            for result in (kg_results or []):
                if result.get("gcs_url"):
                    results["kg_with_gcs_url"] += 1
            
            console.print(f"[green]✓ Found {results['kg_images']} ImageObject nodes in KG[/green]")
            console.print(f"   With GCS URL: {results['kg_with_gcs_url']}")
            console.print(f"   Without GCS URL: {results['kg_images'] - results['kg_with_gcs_url']}")
        except Exception as e:
            console.print(f"[red]✗ Failed to query KG: {e}[/red]")
            logger.exception("KG query failed")
        
        # Test fallback mechanism: Find images in Qdrant missing gcs_url, check if KG has them
        console.print(f"\n[bold cyan]🔄 Testing fallback mechanism...[/bold cyan]")
        fallback_tests = 0
        fallback_success = 0
        
        for point in points[:sample_size]:  # Test first N images
            image_uri = point.payload.get("image_uri", "")
            qdrant_gcs_url = point.payload.get("gcs_url", "")
            
            if not image_uri:
                continue
            
            # If Qdrant is missing gcs_url, check if KG has it
            if not qdrant_gcs_url:
                fallback_tests += 1
                check_query = f"""
                PREFIX schema: <http://schema.org/>
                SELECT ?gcs_url WHERE {{
                    <{image_uri}> schema:contentUrl ?gcs_url .
                }}
                LIMIT 1
                """
                try:
                    kg_fallback_results = await kg.query_graph(check_query)
                    if kg_fallback_results and len(kg_fallback_results) > 0:
                        kg_gcs_url = kg_fallback_results[0].get("gcs_url", "")
                        if kg_gcs_url:
                            fallback_success += 1
                            results["sample_verification"].append({
                                "image_uri": image_uri[:50],
                                "qdrant_has_gcs": False,
                                "kg_has_gcs": True,
                                "kg_gcs_url": kg_gcs_url[:60]
                            })
                except Exception as e:
                    logger.debug(f"Fallback check failed for {image_uri[:50]}: {e}")
        
        results["kg_can_fallback"] = fallback_success
        results["fallback_tests"] = fallback_tests
        
        # Display results
        console.print("\n" + "="*70)
        console.print("[bold]Verification Results[/bold]")
        console.print("="*70)
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Qdrant Images", str(results["qdrant_images"]))
        table.add_row("Qdrant with gcs_url", str(results["qdrant_with_gcs_url"]))
        table.add_row("Qdrant missing gcs_url", str(results["qdrant_missing_gcs_url"]))
        table.add_row("KG ImageObject nodes", str(results["kg_images"]))
        table.add_row("KG with GCS URL", str(results["kg_with_gcs_url"]))
        table.add_row("Fallback tests", str(results["fallback_tests"]))
        table.add_row("Fallback successes", str(results["kg_can_fallback"]))
        
        console.print(table)
        
        # Show sample verification results
        if results["sample_verification"]:
            console.print("\n[bold cyan]Sample Fallback Verifications:[/bold cyan]")
            sample_table = Table(show_header=True, header_style="bold cyan")
            sample_table.add_column("Image URI", style="cyan", max_width=50)
            sample_table.add_column("Qdrant", style="yellow")
            sample_table.add_column("KG", style="green")
            sample_table.add_column("GCS URL", style="blue", max_width=60)
            
            for sample in results["sample_verification"][:5]:  # Show first 5
                sample_table.add_row(
                    sample["image_uri"],
                    "❌ Missing" if not sample["qdrant_has_gcs"] else "✅",
                    "✅ Found" if sample["kg_has_gcs"] else "❌",
                    sample.get("kg_gcs_url", "N/A")
                )
            
            console.print(sample_table)
        
        # Overall assessment
        console.print("\n" + "="*70)
        if results["kg_images"] > 0:
            coverage_pct = (results["kg_images"] / results["qdrant_images"] * 100) if results["qdrant_images"] > 0 else 0
            console.print(f"[bold]Coverage: {coverage_pct:.1f}% of Qdrant images are in KG[/bold]")
            
            if results["kg_with_gcs_url"] > 0:
                gcs_coverage = (results["kg_with_gcs_url"] / results["kg_images"] * 100) if results["kg_images"] > 0 else 0
                console.print(f"[bold]GCS URL Coverage: {gcs_coverage:.1f}% of KG images have GCS URLs[/bold]")
            
            if results["fallback_tests"] > 0:
                fallback_rate = (results["kg_can_fallback"] / results["fallback_tests"] * 100) if results["fallback_tests"] > 0 else 0
                console.print(f"[bold]Fallback Success Rate: {fallback_rate:.1f}%[/bold]")
                
                if fallback_rate > 50:
                    console.print("[bold green]✅ Backfill appears successful! KG can provide fallback for missing Qdrant metadata.[/bold green]")
                elif fallback_rate > 0:
                    console.print("[bold yellow]⚠️  Partial success. Some fallbacks work, but not all.[/bold yellow]")
                else:
                    console.print("[bold red]❌ Fallback mechanism not working. KG may not have been backfilled properly.[/bold red]")
            else:
                console.print("[yellow]⚠️  No fallback tests performed (all sample images had gcs_url in Qdrant)[/yellow]")
        else:
            console.print("[bold red]❌ No images found in KG. Backfill may not have run successfully.[/bold red]")
        
        return results
    
    finally:
        # ALWAYS clean up resources, even if there's an error
        if kg:
            try:
                await kg.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down KG manager: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify KG backfill from Qdrant")
    parser.add_argument("--collection", default="childrens_book_images", help="Qdrant collection name")
    parser.add_argument("--sample-size", type=int, default=10, help="Number of images to test for fallback")
    
    args = parser.parse_args()
    
    result = asyncio.run(verify_backfill(
        collection_name=args.collection,
        sample_size=args.sample_size
    ))
    
    if "error" in result:
        sys.exit(1)
    
    # Exit with error if KG has no images
    if result.get("kg_images", 0) == 0:
        console.print("\n[bold red]Verification failed: No images in KG[/bold red]")
        sys.exit(1)

