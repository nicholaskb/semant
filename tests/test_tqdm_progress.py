#!/usr/bin/env python3
"""
Quick test to demonstrate tqdm progress bars in action
"""

import asyncio
from pathlib import Path
from scripts.generate_childrens_book import ChildrensBookOrchestrator
from rich.console import Console

console = Console()

async def test_progress_bars():
    """Test the ingestion with progress bars"""
    
    console.print("\n[bold cyan]🧪 Testing tqdm Progress Bars[/bold cyan]\n")
    console.print("This will process a small subset of images to show progress bars in action.\n")
    
    # Create orchestrator
    orchestrator = ChildrensBookOrchestrator(
        bucket_name="veo-videos-baro-1759717316",
        input_prefix="input_kids_monster/",
        output_prefix="generated_images/",
    )
    
    await orchestrator.initialize()
    
    # Test just the ingestion step with progress bars
    console.print("[bold]Step 1: Testing Image Ingestion with Progress Bars[/bold]\n")
    
    try:
        result = await orchestrator._run_ingestion(
            extensions=["png", "jpg", "jpeg"],
            overwrite=False
        )
        
        console.print(f"\n[green]✅ Ingestion completed![/green]")
        console.print(f"   Status: {result.get('status', 'unknown')}")
        console.print(f"   Input images: {result.get('input_images_count', 0)}")
        console.print(f"   Output images: {result.get('output_images_count', 0)}")
        console.print(f"   Total: {result.get('successful', 0)}")
        
        return True
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_progress_bars())
    exit(0 if success else 1)

