#!/usr/bin/env python3
"""
End-to-End Integration Test
Tests the complete pipeline: Ingestion → Pairing → Book Generation
"""

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from scripts.generate_childrens_book import ChildrensBookOrchestrator

console = Console()

async def test_end_to_end():
    """Run complete end-to-end test"""
    
    console.print(Panel.fit(
        "[bold cyan]🧪 End-to-End Integration Test[/bold cyan]\n"
        "Testing: Ingestion → Pairing → Book Generation\n"
        "With: All images in KG + Qdrant",
        border_style="cyan"
    ))
    
    # Step 1: Verify ingestion status
    console.print("\n[bold]Step 1: Verifying Ingestion Status[/bold]")
    from verify_ingestion import verify_ingestion
    ingestion_ok = await verify_ingestion()
    
    if not ingestion_ok:
        console.print("\n[yellow]⚠️  Ingestion incomplete. Continuing with available images...[/yellow]")
    
    # Step 2: Test Pairing
    console.print("\n[bold]Step 2: Testing Image Pairing[/bold]")
    try:
        orchestrator = ChildrensBookOrchestrator(
            bucket_name="veo-videos-baro-1759717316",
            input_prefix="input_kids_monster/",
            output_prefix="generated_images/",
        )
        
        await orchestrator.initialize()
        
        # Test pairing
        pairing_result = await orchestrator._run_pairing()
        
        pairs_count = pairing_result.get("pairs_count", 0)
        low_confidence = pairing_result.get("low_confidence_count", 0)
        
        console.print(f"  ✅ Pairing completed!")
        console.print(f"     - Pairs created: {pairs_count}")
        console.print(f"     - Low confidence: {low_confidence}")
        
        if pairs_count == 0:
            console.print("\n[red]❌ No pairs created - cannot continue[/red]")
            return False
        
        # Show sample pairs
        if pairing_result.get("pairs"):
            console.print(f"\n  📋 Sample pairs (first 3):")
            for i, pair in enumerate(pairing_result["pairs"][:3], 1):
                input_name = Path(pair["input_image_uri"]).name if "file://" in pair["input_image_uri"] else pair["input_image_uri"]
                output_count = len(pair.get("output_image_uris", []))
                confidence = pair.get("confidence", 0)
                console.print(f"     {i}. Input: {input_name}")
                console.print(f"        Outputs: {output_count} images")
                console.print(f"        Confidence: {confidence:.2f}")
        
        pairing_ok = True
        
    except Exception as e:
        console.print(f"  ❌ Pairing failed: {e}")
        import traceback
        traceback.print_exc()
        pairing_ok = False
        return False
    
    # Step 3: Test Full Book Generation (limited to first 5 pages for speed)
    console.print("\n[bold]Step 3: Testing Book Generation (First 5 Pages)[/bold]")
    
    # Temporarily limit to 5 pages for testing
    original_max = orchestrator.max_pages
    orchestrator.max_pages = 5
    
    try:
        # Limit pairs to 5 for testing
        limited_pairs = pairing_result["pairs"][:5]
        pairing_result["pairs"] = limited_pairs
        pairing_result["pairs_count"] = len(limited_pairs)
        
        # Test image analysis
        console.print("  📊 Analyzing images...")
        analysis_result = await orchestrator._analyze_images(limited_pairs)
        console.print(f"     ✅ Analyzed {len(analysis_result.get('analyses', []))} pairs")
        
        # Test color arrangement
        console.print("  🎨 Arranging by color...")
        color_result = await orchestrator._arrange_by_color(limited_pairs)
        console.print(f"     ✅ Arranged {len(color_result.get('arrangements', []))} pairs")
        
        # Test layout design
        console.print("  📐 Designing layouts...")
        layout_result = await orchestrator._design_layouts(limited_pairs, color_result)
        console.print(f"     ✅ Designed {len(layout_result.get('layouts', []))} layouts")
        
        # Test book generation
        console.print("  📚 Generating book...")
        book_result = await orchestrator._generate_book_html(limited_pairs, layout_result)
        
        html_path = book_result.get("html_path")
        if html_path and Path(html_path).exists():
            console.print(f"     ✅ Book generated: {html_path}")
            book_ok = True
        else:
            console.print("     ❌ Book file not found")
            book_ok = False
        
        # Restore original max_pages
        orchestrator.max_pages = original_max
        
    except Exception as e:
        console.print(f"  ❌ Book generation failed: {e}")
        import traceback
        traceback.print_exc()
        book_ok = False
        orchestrator.max_pages = original_max
    
    # Summary
    console.print("\n" + "=" * 70)
    console.print("[bold]End-to-End Test Summary[/bold]")
    console.print("=" * 70)
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Step", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")
    
    table.add_row("1. Ingestion", "✅" if ingestion_ok else "⚠️", "Images in KG + Qdrant")
    table.add_row("2. Pairing", "✅" if pairing_ok else "❌", f"{pairs_count} pairs created")
    table.add_row("3. Book Generation", "✅" if book_ok else "❌", "HTML book created" if book_ok else "Failed")
    
    console.print(table)
    
    all_passed = ingestion_ok and pairing_ok and book_ok
    
    if all_passed:
        console.print("\n[bold green]✅ End-to-End Test PASSED![/bold green]")
        console.print("   All components working together successfully.")
    else:
        console.print("\n[bold yellow]⚠️  End-to-End Test PARTIAL[/bold yellow]")
        console.print("   Some steps completed, but not all.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(test_end_to_end())
    sys.exit(0 if success else 1)

