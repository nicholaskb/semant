#!/usr/bin/env python3
"""
Test end-to-end with existing Qdrant data
Since ingestion is still running, we'll test pairing with what's already in Qdrant
"""

import asyncio
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from scripts.generate_childrens_book import ChildrensBookOrchestrator
from qdrant_client import QdrantClient

console = Console()

async def test_with_existing():
    """Test pairing with existing Qdrant embeddings"""
    
    console.print(Panel.fit(
        "[bold cyan]🧪 Testing with Existing Qdrant Data[/bold cyan]\n"
        "Testing pairing with embeddings already in Qdrant",
        border_style="cyan"
    ))
    
    # Check Qdrant status
    console.print("\n[bold]Checking Qdrant Status...[/bold]")
    try:
        qdrant_client = QdrantClient(host="localhost", port=6333)
        collection_info = qdrant_client.get_collection("childrens_book_images")
        qdrant_count = collection_info.points_count
        console.print(f"  ✅ Qdrant has {qdrant_count} embeddings")
        
        if qdrant_count < 100:
            console.print(f"\n[yellow]⚠️  Only {qdrant_count} embeddings found.[/yellow]")
            console.print("   Ingestion may still be running. Continuing anyway...")
    except Exception as e:
        console.print(f"  ❌ Qdrant error: {e}")
        return False
    
    # Test pairing with existing data
    console.print("\n[bold]Testing Image Pairing...[/bold]")
    
    try:
        orchestrator = ChildrensBookOrchestrator(
            bucket_name="veo-videos-baro-1759717316",
            input_prefix="input_kids_monster/",
            output_prefix="generated_images/",
        )
        
        await orchestrator.initialize()
        
        # The pairing will use Qdrant embeddings even if KG is empty
        # because it queries Qdrant directly for similarity search
        console.print("  🔍 Running pairing with Qdrant embeddings...")
        pairing_result = await orchestrator._run_pairing()
        
        pairs_count = pairing_result.get("pairs_count", 0)
        console.print(f"\n  ✅ Pairing completed!")
        console.print(f"     - Pairs created: {pairs_count}")
        
        if pairs_count > 0:
            console.print(f"\n  📋 Sample pairs:")
            for i, pair in enumerate(pairing_result["pairs"][:3], 1):
                input_uri = pair.get("input_image_uri", "unknown")
                output_count = len(pair.get("output_image_uris", []))
                confidence = pair.get("confidence", 0)
                console.print(f"     {i}. Input: {Path(input_uri).name if 'file://' in input_uri else input_uri[:50]}")
                console.print(f"        Outputs: {output_count} images")
                console.print(f"        Confidence: {confidence:.2f}")
            
            return True
        else:
            console.print("\n  ⚠️  No pairs created - KG may need more images")
            console.print("     This is expected if ingestion is still running")
            return False
            
    except Exception as e:
        console.print(f"\n  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_with_existing())
    exit(0 if success else 1)

