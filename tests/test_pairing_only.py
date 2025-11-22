#!/usr/bin/env python3
"""
Test pairing step only with already-ingested images
"""

import asyncio
from pathlib import Path
from scripts.generate_childrens_book import ChildrensBookOrchestrator
from rich.console import Console

console = Console()

async def test_pairing_with_existing():
    """Test pairing with images already in KG/Qdrant"""
    
    # Find the most recent book directory
    book_dirs = sorted(Path("generated_books").glob("childrens_book_*"), reverse=True)
    if not book_dirs:
        console.print("[red]❌ No book directories found[/red]")
        return
    
    book_dir = book_dirs[0]
    console.print(f"[cyan]Using directory: {book_dir}[/cyan]")
    
    # Check if we have images
    input_dir = book_dir / "input"
    output_dir = book_dir / "output"
    
    if not input_dir.exists():
        console.print(f"[red]❌ Input directory not found: {input_dir}[/red]")
        return
    
    input_count = len(list(input_dir.glob("*.png"))) + len(list(input_dir.glob("*.jpg")))
    console.print(f"[green]✅ Found {input_count} input images[/green]")
    
    # Create orchestrator (will initialize with embeddings)
    orchestrator = ChildrensBookOrchestrator(
        bucket_name="veo-videos-baro-1759717316",
        input_prefix="input_kids_monster/",
        output_prefix="generated_images/",
    )
    
    await orchestrator.initialize()
    
    # Test pairing only
    console.print("\n[bold cyan]Testing Pairing Step...[/bold cyan]")
    try:
        pairing_result = await orchestrator._run_pairing()
        
        console.print(f"\n[green]✅ Pairing completed![/green]")
        console.print(f"   Pairs created: {pairing_result.get('pairs_count', 0)}")
        console.print(f"   Low confidence: {pairing_result.get('low_confidence_count', 0)}")
        
        if pairing_result.get('pairs'):
            console.print(f"\n[bold]First few pairs:[/bold]")
            for i, pair in enumerate(pairing_result['pairs'][:3], 1):
                console.print(f"   {i}. Input: {Path(pair['input_image_uri']).name}")
                console.print(f"      Outputs: {len(pair.get('output_image_uris', []))} images")
                console.print(f"      Confidence: {pair.get('confidence', 0):.2f}")
        
        return True
    except Exception as e:
        console.print(f"[red]❌ Pairing failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pairing_with_existing())
    exit(0 if success else 1)

