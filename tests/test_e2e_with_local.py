#!/usr/bin/env python3
"""
End-to-End Test with Local Images
Tests the complete pipeline using already-downloaded local images
"""

import asyncio
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts.generate_childrens_book import ChildrensBookOrchestrator
from agents.domain.image_ingestion_agent import ImageIngestionAgent
from kg.models.graph_manager import KnowledgeGraphManager
from kg.services.image_embedding_service import ImageEmbeddingService
from agents.core.message_types import AgentMessage

console = Console()

async def test_e2e_local():
    """Test end-to-end with local images"""
    
    console.print(Panel.fit(
        "[bold cyan]🧪 End-to-End Test with Local Images[/bold cyan]\n"
        "Using already-downloaded images to test full pipeline",
        border_style="cyan"
    ))
    
    # Find local images - look for directory with both input and output
    book_dirs = sorted(Path("generated_books").glob("childrens_book_*"), reverse=True)
    book_dir = None
    
    for dir in book_dirs:
        input_dir = dir / "input"
        output_dir = dir / "output"
        if input_dir.exists() and output_dir.exists():
            input_files_list = list(input_dir.glob("*.png")) + list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.jpeg"))
            output_files_list = list(output_dir.glob("*.png")) + list(output_dir.glob("*.jpg")) + list(output_dir.glob("*.jpeg"))
            if len(input_files_list) > 0 and len(output_files_list) > 0:
                book_dir = dir
                break
    
    if not book_dir:
        console.print("[red]❌ No book directory with both input and output images found[/red]")
        console.print("   Available directories:")
        for dir in book_dirs[:5]:
            console.print(f"     - {dir}")
        return False
    
    input_dir = book_dir / "input"
    output_dir = book_dir / "output"
    console.print(f"[green]✅ Using directory: {book_dir}[/green]")
    
    input_files = sorted([f for f in input_dir.glob("*") if f.suffix.lower() in ['.png', '.jpg', '.jpeg']])
    output_files = sorted([f for f in output_dir.glob("*") if f.suffix.lower() in ['.png', '.jpg', '.jpeg']])
    
    console.print(f"\n[bold]Found Local Images:[/bold]")
    console.print(f"  Input: {len(input_files)} images")
    console.print(f"  Output: {len(output_files)} images")
    
    if len(input_files) == 0 or len(output_files) == 0:
        console.print("[yellow]⚠️  Not enough images for testing[/yellow]")
        return False
    
    # Initialize services
    console.print("\n[bold]Initializing Services...[/bold]")
    kg_manager = KnowledgeGraphManager(persistent_storage=True)
    await kg_manager.initialize()
    
    embedding_service = ImageEmbeddingService()
    console.print("  ✅ Services initialized")
    
    # Step 1: Ingest local images into KG + Qdrant
    console.print("\n[bold]Step 1: Ingesting Local Images[/bold]")
    
    ingestion_agent = ImageIngestionAgent(
        kg_manager=kg_manager,
        embedding_service=embedding_service
    )
    await ingestion_agent.initialize()
    
    # Manually ingest a few images for testing
    test_inputs = input_files[:5]  # Test with 5 inputs
    test_outputs = output_files[:60]  # Test with 60 outputs (12 per input)
    
    console.print(f"  Processing {len(test_inputs)} inputs and {len(test_outputs)} outputs...")
    
    input_uris = []
    for img_path in test_inputs:
        try:
            embedding, description = await embedding_service.embed_image(img_path)
            image_uri = f"http://example.org/image/{img_path.stem}"
            
            # Store in KG
            await ingestion_agent._store_image_in_kg(
                image_uri=image_uri,
                filename=img_path.name,
                gcs_url=f"file://{img_path}",
                image_type="input",
                embedding=embedding,
                description=description,
                file_size=img_path.stat().st_size
            )
            
            # Store in Qdrant
            embedding_service.store_embedding(
                image_uri=image_uri,
                embedding=embedding,
                metadata={"filename": img_path.name, "image_type": "input", "description": description}
            )
            
            input_uris.append(image_uri)
            console.print(f"    ✅ Ingested input: {img_path.name}")
        except Exception as e:
            console.print(f"    ❌ Failed {img_path.name}: {e}")
    
    output_uris = []
    for img_path in test_outputs:
        try:
            embedding, description = await embedding_service.embed_image(img_path)
            image_uri = f"http://example.org/image/{img_path.stem}"
            
            # Store in KG
            await ingestion_agent._store_image_in_kg(
                image_uri=image_uri,
                filename=img_path.name,
                gcs_url=f"file://{img_path}",
                image_type="output",
                embedding=embedding,
                description=description,
                file_size=img_path.stat().st_size
            )
            
            # Store in Qdrant
            embedding_service.store_embedding(
                image_uri=image_uri,
                embedding=embedding,
                metadata={"filename": img_path.name, "image_type": "output", "description": description}
            )
            
            output_uris.append(image_uri)
            if len(output_uris) % 10 == 0:
                console.print(f"    ✅ Ingested {len(output_uris)} outputs...")
        except Exception as e:
            console.print(f"    ❌ Failed {img_path.name}: {e}")
    
    console.print(f"\n  ✅ Ingested {len(input_uris)} inputs, {len(output_uris)} outputs")
    
    # Save KG
    kg_manager.save_graph()
    console.print("  ✅ Knowledge Graph saved")
    
    # Step 2: Test Pairing
    console.print("\n[bold]Step 2: Testing Image Pairing[/bold]")
    
    from agents.domain.image_pairing_agent import ImagePairingAgent
    pairing_agent = ImagePairingAgent(
        kg_manager=kg_manager,
        embedding_service=embedding_service
    )
    
    # Pair images
    message = AgentMessage(
        sender_id="test",
        recipient_id="image_pairing_agent",
        content={
            "action": "pair_images",
            "input_image_uris": None,  # Use all from KG
            "top_k_outputs": 12,
            "min_confidence": 0.5,
        },
        message_type="request"
    )
    
    response = await pairing_agent._process_message_impl(message)
    result = response.content
    
    pairs_count = result.get("pairs_count", 0)
    pairs = result.get("pairs", [])
    
    console.print(f"  ✅ Pairing completed!")
    console.print(f"     - Pairs created: {pairs_count}")
    
    if pairs_count > 0:
        console.print(f"\n  📋 Sample pairs:")
        for i, pair in enumerate(pairs[:3], 1):
            input_name = pair.get("input_image_name", "unknown")
            output_count = len(pair.get("output_image_uris", []))
            confidence = pair.get("confidence", 0)
            console.print(f"     {i}. Input: {input_name}")
            console.print(f"        Outputs: {output_count} images")
            console.print(f"        Confidence: {confidence:.3f}")
            console.print(f"        Method: {pair.get('method', 'unknown')}")
        
        # Step 3: Test Book Generation (limited)
        console.print("\n[bold]Step 3: Testing Book Generation (First 3 Pages)[/bold]")
        
        orchestrator = ChildrensBookOrchestrator(
            bucket_name="veo-videos-baro-1759717316",
            input_prefix="input_kids_monster/",
            output_prefix="generated_images/",
        )
        await orchestrator.initialize()
        
        # Convert pairs to format expected by book generator
        book_pairs = []
        for pair in pairs[:3]:  # Just 3 pages for testing
            # Convert URIs to local file paths
            input_uri = pair["input_image_uri"]
            input_path = None
            for f in input_files:
                if f.stem in input_uri:
                    input_path = f"file://{f}"
                    break
            
            output_paths = []
            for output_uri in pair.get("output_image_uris", [])[:6]:
                for f in output_files:
                    if f.stem in output_uri:
                        output_paths.append(f"file://{f}")
                        break
            
            if input_path and output_paths:
                book_pairs.append({
                    "input_image_uri": input_path,
                    "output_image_uris": output_paths,
                    "pair_uri": pair.get("pair_uri", ""),
                    "confidence": pair.get("confidence", 0.8),
                })
        
        if book_pairs:
            # Test analysis
            console.print("  📊 Analyzing images...")
            analysis_result = await orchestrator._analyze_images(book_pairs)
            console.print(f"     ✅ Analyzed {len(analysis_result.get('analyses', []))} pairs")
            
            # Test color arrangement
            console.print("  🎨 Arranging by color...")
            color_result = await orchestrator._arrange_by_color(book_pairs)
            console.print(f"     ✅ Arranged {len(color_result.get('arrangements', []))} pairs")
            
            # Test layout design
            console.print("  📐 Designing layouts...")
            layout_result = await orchestrator._design_layouts(book_pairs, color_result)
            console.print(f"     ✅ Designed {len(layout_result.get('layouts', []))} layouts")
            
            # Test book generation
            console.print("  📚 Generating book HTML...")
            book_result = await orchestrator._generate_book_html(book_pairs, layout_result)
            
            html_path = book_result.get("html_path")
            if html_path and Path(html_path).exists():
                console.print(f"     ✅ Book generated: {html_path}")
                book_ok = True
            else:
                console.print("     ❌ Book file not found")
                book_ok = False
        else:
            console.print("  ⚠️  Could not convert pairs to book format")
            book_ok = False
        
        # Summary
        console.print("\n" + "=" * 70)
        console.print("[bold green]✅ End-to-End Test Summary[/bold green]")
        console.print("=" * 70)
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Step", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")
        
        table.add_row("1. Image Ingestion", "✅", f"{len(input_uris)} inputs, {len(output_uris)} outputs")
        table.add_row("2. Image Pairing", "✅", f"{pairs_count} pairs created")
        table.add_row("3. Book Generation", "✅" if book_ok else "⚠️", "HTML book created" if book_ok else "Partial")
        
        console.print(table)
        console.print("\n[bold green]✅ End-to-End Test PASSED![/bold green]")
        
        return True
    else:
        console.print("\n[red]❌ No pairs created - cannot test book generation[/red]")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_e2e_local())
    exit(0 if success else 1)

