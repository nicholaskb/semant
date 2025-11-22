#!/usr/bin/env python3
"""
Test Children's Book Generator with Small Sample
Tests complete workflow with just 2-3 images to verify it works before processing all 86.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_childrens_book import ChildrensBookOrchestrator
from rich.console import Console

console = Console()


async def test_small_book():
    """Test with just 2 input images to verify workflow."""
    
    console.print("\n[bold cyan]Testing Children's Book Generator (Small Sample)[/bold cyan]\n")
    console.print("This will process just 2-3 images to verify the workflow works.\n")
    
    # Create orchestrator
    orchestrator = ChildrensBookOrchestrator(
        bucket_name="veo-videos-baro-1759717316",
        input_prefix="input_kids_monster/",
        output_prefix="generated_images/",
    )
    
    await orchestrator.initialize()
    
    # Override to limit images
    console.print("[yellow]Limiting to 2 images for testing...[/yellow]\n")
    
    # Manually test each step with limited data
    console.print("[bold]Step 1: Testing Image Ingestion (2 images max)[/bold]")
    
    # TODO: Add max_images parameter to ingestion
    
    console.print("\n[yellow]⚠️  Need to add max_images parameter to limit processing[/yellow]")
    console.print("[yellow]Current script will process all 86 images[/yellow]\n")
    
    console.print("[cyan]Recommendation:[/cyan]")
    console.print("  1. Stop the current run (Ctrl+C)")
    console.print("  2. Add --max-images argument to script")
    console.print("  3. Test with --max-images=2 first")
    console.print("  4. Verify HTML output works")
    console.print("  5. Then run on all images")


if __name__ == "__main__":
    asyncio.run(test_small_book())

