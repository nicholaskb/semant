#!/usr/bin/env python3
"""
Diagnostic Script: Find Input → Output Image Pairs

This script:
1. Queries KG for all input images
2. For each input, searches Qdrant for matching output images
3. Displays pairs with confidence scores
4. Shows which GenAI outputs were generated from which inputs

Usage:
    python scripts/diagnose_image_pairing.py [--limit N] [--min-confidence 0.5]
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from loguru import logger

from agents.core.base_agent import AgentMessage
from agents.domain.image_pairing_agent import ImagePairingAgent
from kg.models.graph_manager import KnowledgeGraphManager

console = Console()


async def diagnose_pairing(
    top_k_outputs: int = 12,
    min_confidence: float = 0.5,
    limit_inputs: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run the pairing agent and display results.
    
    Args:
        top_k_outputs: Max outputs per input
        min_confidence: Minimum confidence threshold
        limit_inputs: Limit number of inputs to process (None = all)
    
    Returns:
        Dict with pairing results
    """
    console.print(Panel.fit(
        "[bold cyan]🔍 Image Pairing Diagnostic[/bold cyan]\n"
        f"Finding GenAI outputs that match input images\n"
        f"Settings: top_k={top_k_outputs}, min_confidence={min_confidence}",
        border_style="cyan"
    ))
    
    # Initialize agents
    console.print("\n[yellow]→[/yellow] Initializing agents...")
    try:
        kg_manager = KnowledgeGraphManager()
        await kg_manager.initialize()
        console.print("  ✅ Knowledge Graph initialized")
        
        pairing_agent = ImagePairingAgent(kg_manager=kg_manager)
        console.print("  ✅ ImagePairingAgent initialized")
        
        if not pairing_agent.embedding_service:
            console.print("[red]❌[/red] Embedding service not available!")
            console.print("   Make sure Qdrant is running and images are ingested.")
            return {"error": "Embedding service unavailable"}
        
        console.print("  ✅ Embedding service ready")
        
    except Exception as e:
        console.print(f"[red]❌[/red] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    
    # Run pairing
    console.print("\n[yellow]→[/yellow] Running pairing workflow...")
    try:
        message = AgentMessage(
            sender_id="diagnostic_script",
            recipient_id="image_pairing_agent",
            content={
                "action": "pair_images",
                "top_k_outputs": top_k_outputs,
                "min_confidence": min_confidence,
            },
            message_type="request",
            timestamp=datetime.utcnow().isoformat()
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Pairing images...", total=None)
            response = await pairing_agent._process_message_impl(message)
            progress.update(task, completed=True)
        
        if response.message_type == "error":
            console.print(f"[red]❌[/red] Pairing failed: {response.content}")
            return {"error": response.content}
        
        results = response.content
        console.print(f"\n[green]✅[/green] Pairing complete!")
        
        return results
        
    except Exception as e:
        console.print(f"[red]❌[/red] Pairing error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def display_pairing_results(results: Dict[str, Any]) -> None:
    """Display pairing results in a formatted table."""
    
    if "error" in results:
        console.print(f"\n[red]Error: {results['error']}[/red]")
        return
    
    pairs_count = results.get("pairs_count", 0)
    low_confidence_count = results.get("low_confidence_count", 0)
    pairs = results.get("pairs", [])
    
    if pairs_count == 0:
        console.print("\n[yellow]⚠️[/yellow] No pairs found!")
        console.print("   Possible reasons:")
        console.print("   - No input images in KG")
        console.print("   - No output images in Qdrant")
        console.print("   - Confidence threshold too high")
        console.print("   - Images not ingested yet")
        return
    
    # Summary panel
    summary = Panel.fit(
        f"[bold]Pairs Created:[/bold] {pairs_count}\n"
        f"[bold]Low Confidence:[/bold] {low_confidence_count} (need review)\n"
        f"[bold]High Confidence:[/bold] {pairs_count - low_confidence_count}",
        title="Pairing Summary",
        border_style="green" if pairs_count > 0 else "yellow"
    )
    console.print(summary)
    
    # Detailed pairs table
    table = Table(
        title="Input → Output Image Pairs",
        show_header=True,
        header_style="bold cyan",
        show_lines=True
    )
    table.add_column("Input Image", style="cyan", width=30)
    table.add_column("Output Images", style="green", width=40)
    table.add_column("Confidence", justify="right", width=12)
    table.add_column("Scores", style="dim", width=30)
    table.add_column("Status", width=12)
    
    for pair in pairs:
        input_name = pair.get("input_image_name", "Unknown")
        output_uris = pair.get("output_image_uris", [])
        output_names = pair.get("output_image_names", [])
        confidence = pair.get("confidence", 0.0)
        
        # Format output names (show first 3, then "... +N more")
        if len(output_names) <= 3:
            outputs_display = ", ".join(output_names)
        else:
            outputs_display = ", ".join(output_names[:3]) + f" ... +{len(output_names) - 3} more"
        
        # Get detailed scores
        output_scores = pair.get("output_scores", [])
        if output_scores:
            top_score = output_scores[0]
            embedding_score = top_score.get("embedding_score", 0.0)
            filename_score = top_score.get("filename_score", 0.0)
            metadata_score = top_score.get("metadata_score", 0.0)
            scores_display = f"Emb:{embedding_score:.2f} Fil:{filename_score:.2f} Met:{metadata_score:.2f}"
        else:
            scores_display = "N/A"
        
        # Status indicator
        if confidence >= 0.8:
            status = "[green]✓ High[/green]"
        elif confidence >= 0.7:
            status = "[yellow]⚠ Medium[/yellow]"
        else:
            status = "[red]✗ Low[/red]"
        
        # Confidence bar
        bar_length = int(confidence * 10)
        bar = "█" * bar_length + "░" * (10 - bar_length)
        confidence_display = f"{confidence:.3f} {bar}"
        
        table.add_row(
            input_name,
            outputs_display,
            confidence_display,
            scores_display,
            status
        )
    
    console.print("\n")
    console.print(table)
    
    # Show detailed breakdown for first pair
    if pairs:
        console.print("\n[bold cyan]Detailed Breakdown (First Pair):[/bold cyan]")
        first_pair = pairs[0]
        console.print(f"  Input: {first_pair.get('input_image_name', 'Unknown')}")
        console.print(f"  Confidence: {first_pair.get('confidence', 0.0):.3f}")
        console.print(f"  Method: {first_pair.get('method', 'unknown')}")
        
        output_scores = first_pair.get("output_scores", [])
        if output_scores:
            console.print(f"\n  Top Output Matches:")
            for i, score_info in enumerate(output_scores[:5], 1):
                output_name = score_info.get("output_name", "Unknown")
                final_score = score_info.get("final_score", 0.0)
                emb_score = score_info.get("embedding_score", 0.0)
                filename_score = score_info.get("filename_score", 0.0)
                metadata_score = score_info.get("metadata_score", 0.0)
                
                console.print(f"    {i}. {output_name}")
                console.print(f"       Final: {final_score:.3f} | "
                            f"Embedding: {emb_score:.3f} ({emb_score*0.6:.3f}) | "
                            f"Filename: {filename_score:.3f} ({filename_score*0.2:.3f}) | "
                            f"Metadata: {metadata_score:.3f} ({metadata_score*0.2:.3f})")


async def verify_qdrant_status() -> bool:
    """Verify Qdrant has images before running pairing."""
    console.print("\n[yellow]→[/yellow] Verifying Qdrant status...")
    
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(host="localhost", port=6333)
        
        # Check collection exists
        try:
            collection_info = client.get_collection("childrens_book_images")
            point_count = collection_info.points_count
            console.print(f"  ✅ Collection exists: {point_count} images")
            
            if point_count == 0:
                console.print("[yellow]⚠️[/yellow] Qdrant is empty - no images ingested yet")
                console.print("\n   [bold]Next steps:[/bold]")
                console.print("   1. Run image ingestion:")
                console.print("      python scripts/ingest_gcs_images_to_qdrant.py")
                console.print("   2. Or use the API:")
                console.print("      POST /api/images/index with image_type='input'")
                return False
            
            # Get ALL points to check image_type distribution (not just sample)
            all_points = client.scroll(
                collection_name="childrens_book_images",
                limit=point_count  # Get all points
            )[0]
            
            input_count = sum(1 for p in all_points if p.payload.get("image_type") == "input")
            output_count = sum(1 for p in all_points if p.payload.get("image_type") == "output")
            no_type = sum(1 for p in all_points if "image_type" not in p.payload)
            
            console.print(f"  ✅ Distribution: {input_count} inputs, {output_count} outputs")
            if no_type > 0:
                console.print(f"  ⚠️  {no_type} images without image_type metadata")
            
            if input_count == 0:
                console.print("\n[yellow]⚠️[/yellow] [bold]CRITICAL: No input images found in Qdrant![/bold]")
                console.print("   Pairing requires input images to match against outputs.")
                console.print("\n   [bold]To fix:[/bold]")
                console.print("   1. Ingest input images from GCS:")
                console.print("      python scripts/ingest_gcs_images_to_qdrant.py --input-only")
                console.print("   2. Or use ImageIngestionAgent:")
                console.print("      from agents.domain.image_ingestion_agent import ImageIngestionAgent")
                console.print("      agent = ImageIngestionAgent()")
                console.print("      await agent.ingest_images(input_prefix='input_kids_monster/')")
                return False
            
            if output_count == 0:
                console.print("\n[yellow]⚠️[/yellow] No output images found in Qdrant")
                console.print("   Pairing requires output images to match against inputs.")
                console.print("\n   [bold]To fix:[/bold]")
                console.print("   1. Ingest output images from GCS:")
                console.print("      python scripts/ingest_gcs_images_to_qdrant.py --output-only")
                return False
            
            return True
            
        except Exception as e:
            console.print(f"  [red]❌[/red] Collection check failed: {e}")
            return False
            
    except Exception as e:
        console.print(f"  [red]❌[/red] Qdrant connection failed: {e}")
        console.print("   Make sure Qdrant is running: docker run -d -p 6333:6333 qdrant/qdrant")
        return False


async def verify_kg_status() -> bool:
    """Verify KG has input images before running pairing."""
    console.print("\n[yellow]→[/yellow] Verifying Knowledge Graph status...")
    
    try:
        kg_manager = KnowledgeGraphManager()
        await kg_manager.initialize()
        
        # Query for input images (same query as pairing agent uses)
        query = """
        PREFIX schema: <http://schema.org/>
        PREFIX kg: <http://example.org/kg#>
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT (COUNT(?image) as ?count) WHERE {
            ?image a book:InputImage ;
                   schema:name ?name ;
                   schema:contentUrl ?url ;
                   kg:hasEmbedding ?hasEmbedding .
            FILTER (?hasEmbedding = "true")
        }
        """
        
        results = await kg_manager.query_graph(query)
        input_count = int(results[0]["count"]) if results else 0
        
        # Query for output images
        query_output = """
        PREFIX schema: <http://schema.org/>
        PREFIX kg: <http://example.org/kg#>
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT (COUNT(?image) as ?count) WHERE {
            ?image a book:OutputImage ;
                   schema:name ?name ;
                   schema:contentUrl ?url ;
                   kg:hasEmbedding ?hasEmbedding .
            FILTER (?hasEmbedding = "true")
        }
        """
        
        results_output = await kg_manager.query_graph(query_output)
        output_count = int(results_output[0]["count"]) if results_output else 0
        
        console.print(f"  ✅ KG: {input_count} input images, {output_count} output images")
        
        if input_count == 0:
            console.print("\n[yellow]⚠️[/yellow] [bold]CRITICAL: No input images in Knowledge Graph![/bold]")
            console.print("   Pairing agent queries KG for book:InputImage types.")
            console.print("   If KG is empty, pairing will find no inputs to match.")
            console.print("\n   [bold]To fix:[/bold]")
            console.print("   1. Ensure images are ingested with image_type='input'")
            console.print("   2. Images must be stored as book:InputImage in KG")
            console.print("   3. Run backfill if Qdrant has images but KG doesn't:")
            console.print("      python scripts/backfill_kg_from_qdrant.py")
            return False
        
        await kg_manager.shutdown()
        return True
        
    except Exception as e:
        console.print(f"  [red]❌[/red] KG check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main diagnostic function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Diagnose image pairing: Find GenAI outputs that match input images"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=12,
        help="Maximum outputs per input (default: 12)"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum confidence threshold (default: 0.5)"
    )
    parser.add_argument(
        "--limit-inputs",
        type=int,
        default=None,
        help="Limit number of inputs to process (default: all)"
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip Qdrant verification"
    )
    
    args = parser.parse_args()
    
    # Verify Qdrant and KG status
    if not args.skip_verify:
        qdrant_ok = await verify_qdrant_status()
        kg_ok = await verify_kg_status()
        
        if not qdrant_ok or not kg_ok:
            console.print("\n[yellow]⚠️[/yellow] Verification failed.")
            console.print("   Fix the issues above, or use --skip-verify to proceed anyway")
            response = input("\nContinue anyway? (y/N): ")
            if response.lower() != 'y':
                return 1
    
    # Run pairing
    results = await diagnose_pairing(
        top_k_outputs=args.top_k,
        min_confidence=args.min_confidence,
        limit_inputs=args.limit_inputs
    )
    
    # Display results
    display_pairing_results(results)
    
    # Final status
    if "error" in results:
        console.print("\n[red]❌ Diagnostic failed[/red]")
        return 1
    elif results.get("pairs_count", 0) == 0:
        console.print("\n[yellow]⚠️[/yellow] No pairs found - check ingestion status")
        return 1
    else:
        console.print("\n[green]✅ Diagnostic complete![/green]")
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)

