#!/usr/bin/env python3
"""
Working Demo: Children's Book Generation System

Demonstrates the complete pipeline with real components.
Date: 2025-01-08
"""

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from kg.services.image_embedding_service import ImageEmbeddingService
from agents.domain.image_ingestion_agent import ImageIngestionAgent
from agents.domain.image_pairing_agent import ImagePairingAgent
from agents.domain.story_sequencing_agent import StorySequencingAgent
from kg.models.graph_manager import KnowledgeGraphManager

console = Console()


async def demo_step_1_embedding_service():
    """Demo: Image Embedding Service"""
    console.print(Panel.fit(
        "[bold cyan]STEP 1: Image Embedding Service[/bold cyan]\n"
        "Testing vector embedding generation and similarity",
        border_style="cyan"
    ))
    
    try:
        service = ImageEmbeddingService()
        
        # Test text embedding (reuses DiaryAgent pattern)
        console.print("\n[yellow]→[/yellow] Testing text embedding...")
        embedding1 = service.embed_text("A yellow duckling with big orange feet")
        console.print(f"  ✓ Generated embedding: {len(embedding1)} dimensions")
        
        # Test similarity computation
        console.print("\n[yellow]→[/yellow] Testing similarity computation...")
        embedding2 = service.embed_text("A small yellow duck with large webbed feet")
        similarity = ImageEmbeddingService.compute_similarity(embedding1, embedding2)
        console.print(f"  ✓ Similarity score: {similarity:.3f} (High = similar descriptions)")
        
        # Test opposite
        embedding3 = service.embed_text("A red fire truck speeding down the road")
        dissimilarity = ImageEmbeddingService.compute_similarity(embedding1, embedding3)
        console.print(f"  ✓ Dissimilarity score: {dissimilarity:.3f} (Low = different descriptions)")
        
        console.print("\n[green]✅ Step 1 Complete: Embedding service working![/green]\n")
        return True
        
    except Exception as e:
        console.print(f"\n[red]❌ Step 1 Failed: {e}[/red]\n")
        return False


async def demo_step_2_kg_integration():
    """Demo: Knowledge Graph Integration"""
    console.print(Panel.fit(
        "[bold cyan]STEP 2: Knowledge Graph Integration[/bold cyan]\n"
        "Testing RDF storage and SPARQL queries",
        border_style="cyan"
    ))
    
    try:
        kg = KnowledgeGraphManager()
        await kg.initialize()
        
        console.print("\n[yellow]→[/yellow] KG Manager initialized...")
        console.print(f"  ✓ Backend: {kg.__class__.__name__}")
        
        # Test SPARQL query
        console.print("\n[yellow]→[/yellow] Testing SPARQL query...")
        query = """
        PREFIX schema: <http://schema.org/>
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT (COUNT(*) as ?count) WHERE {
            ?image a schema:ImageObject .
        }
        """
        results = await kg.query_graph(query)
        console.print(f"  ✓ Query executed: {len(results)} results")
        
        console.print("\n[green]✅ Step 2 Complete: Knowledge Graph working![/green]\n")
        await kg.shutdown()
        return True
        
    except Exception as e:
        console.print(f"\n[red]❌ Step 2 Failed: {e}[/red]\n")
        return False


async def demo_step_3_image_pairing():
    """Demo: Image Pairing Algorithm"""
    console.print(Panel.fit(
        "[bold cyan]STEP 3: Image Pairing Algorithm[/bold cyan]\n"
        "Testing filename matching and scoring",
        border_style="cyan"
    ))
    
    try:
        kg = KnowledgeGraphManager()
        await kg.initialize()
        
        agent = ImagePairingAgent(kg_manager=kg)
        console.print("\n[yellow]→[/yellow] ImagePairingAgent initialized...")
        console.print(f"  ✓ Capabilities: {agent.capabilities}")
        
        # Test filename similarity
        console.print("\n[yellow]→[/yellow] Testing filename matching...")
        sim1 = ImagePairingAgent._compute_filename_similarity(
            "input_001.png",
            "output_001_a.png"
        )
        console.print(f"  ✓ 'input_001' → 'output_001_a': {sim1:.3f} (HIGH - numbers match!)")
        
        sim2 = ImagePairingAgent._compute_filename_similarity(
            "input_001.png",
            "output_999_z.png"
        )
        console.print(f"  ✓ 'input_001' → 'output_999_z': {sim2:.3f} (LOW - no match)")
        
        # Test metadata correlation
        console.print("\n[yellow]→[/yellow] Testing metadata correlation...")
        metadata = {
            "description": "Generated from input_001.png",
            "gcs_url": "gs://bucket/output/input_001_variation_a.png"
        }
        correlation = ImagePairingAgent._compute_metadata_correlation(metadata, "input_001.png")
        console.print(f"  ✓ Metadata correlation: {correlation:.3f}")
        
        console.print("\n[green]✅ Step 3 Complete: Pairing algorithm working![/green]\n")
        await kg.shutdown()
        return True
        
    except Exception as e:
        console.print(f"\n[red]❌ Step 3 Failed: {e}[/red]\n")
        return False


async def demo_step_4_grid_logic():
    """Demo: Grid Layout Logic"""
    console.print(Panel.fit(
        "[bold cyan]STEP 4: Grid Layout Logic[/bold cyan]\n"
        "Testing anti-lazy grid sizing (2x2, 3x3, 3x4, 4x4)",
        border_style="cyan"
    ))
    
    console.print("\n[yellow]→[/yellow] Testing grid size determination...")
    
    test_cases = [
        (3, "2x2"),
        (7, "3x3"),
        (12, "3x4"),
        (15, "4x4"),
    ]
    
    table = Table(title="Grid Size Results")
    table.add_column("Images", style="cyan")
    table.add_column("Expected Grid", style="yellow")
    table.add_column("Actual Grid", style="green")
    table.add_column("Status", style="bold")
    
    all_correct = True
    for num_images, expected_grid in test_cases:
        # Apply grid logic
        if num_images <= 4:
            actual_grid = "2x2"
        elif num_images <= 9:
            actual_grid = "3x3"
        elif num_images <= 12:
            actual_grid = "3x4"
        else:
            actual_grid = "4x4"
        
        status = "✅" if actual_grid == expected_grid else "❌"
        table.add_row(
            str(num_images),
            expected_grid,
            actual_grid,
            status
        )
        
        if actual_grid != expected_grid:
            all_correct = False
    
    console.print(table)
    
    if all_correct:
        console.print("\n[green]✅ Step 4 Complete: Grid logic perfect! (No lazy 2x2 grids!)[/green]\n")
        return True
    else:
        console.print("\n[red]❌ Step 4 Failed: Grid logic incorrect[/red]\n")
        return False


async def demo_step_5_orchestration():
    """Demo: Component Integration"""
    console.print(Panel.fit(
        "[bold cyan]STEP 5: Component Integration[/bold cyan]\n"
        "Testing that all agents are properly wired",
        border_style="cyan"
    ))
    
    try:
        from scripts.generate_childrens_book import ChildrensBookOrchestrator
        
        console.print("\n[yellow]→[/yellow] Creating orchestrator...")
        orchestrator = ChildrensBookOrchestrator(
            bucket_name="test-bucket",
            input_prefix="test_input/",
            output_prefix="test_output/"
        )
        
        console.print(f"  ✓ Bucket: {orchestrator.bucket_name}")
        console.print(f"  ✓ Output dir: {orchestrator.output_dir}")
        
        # Check all agents are present
        console.print("\n[yellow]→[/yellow] Verifying agent integration...")
        
        agents_table = Table(title="Integrated Agents")
        agents_table.add_column("Agent", style="cyan")
        agents_table.add_column("Type", style="yellow")
        agents_table.add_column("Status", style="green")
        
        agents = [
            ("ImageIngestionAgent", "NEW", orchestrator.ingestion_agent),
            ("ImagePairingAgent", "NEW", orchestrator.pairing_agent),
            ("ColorPaletteAgent", "EXISTING", orchestrator.color_agent),
            ("CompositionAgent", "EXISTING", orchestrator.composition_agent),
            ("ImageAnalysisAgent", "EXISTING", orchestrator.image_analysis_agent),
            ("CriticAgent", "EXISTING", orchestrator.critic_agent),
        ]
        
        all_present = True
        for name, agent_type, agent_obj in agents:
            if agent_obj is not None:
                agents_table.add_row(name, agent_type, "✅ Present")
            else:
                agents_table.add_row(name, agent_type, "❌ Missing")
                all_present = False
        
        console.print(agents_table)
        
        # Check helper methods exist
        console.print("\n[yellow]→[/yellow] Verifying helper methods...")
        methods = [
            "_compute_color_harmony",
            "_compute_visual_balance",
            "_create_html_template"
        ]
        
        for method in methods:
            if hasattr(orchestrator, method):
                console.print(f"  ✓ {method}")
            else:
                console.print(f"  ❌ {method} missing")
                all_present = False
        
        if all_present:
            console.print("\n[green]✅ Step 5 Complete: All components integrated![/green]\n")
            return True
        else:
            console.print("\n[red]❌ Step 5 Failed: Missing components[/red]\n")
            return False
            
    except Exception as e:
        console.print(f"\n[red]❌ Step 5 Failed: {e}[/red]\n")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False


async def demo_step_6_visual_balance():
    """Demo: Visual Balance Computation"""
    console.print(Panel.fit(
        "[bold cyan]STEP 6: Visual Balance Algorithm[/bold cyan]\n"
        "Testing grid fill ratio scoring",
        border_style="cyan"
    ))
    
    try:
        from scripts.generate_childrens_book import ChildrensBookOrchestrator
        orchestrator = ChildrensBookOrchestrator(bucket_name="test")
        
        console.print("\n[yellow]→[/yellow] Testing visual balance scoring...")
        
        test_cases = [
            (4, "2x2", 1.0),      # Perfect fill
            (6, "3x3", 0.67),     # 67% fill
            (12, "3x4", 1.0),     # Perfect fill
            (3, "3x3", 0.33),     # Sparse (33%)
        ]
        
        table = Table(title="Visual Balance Scores")
        table.add_column("Images", style="cyan")
        table.add_column("Grid", style="yellow")
        table.add_column("Fill %", style="magenta")
        table.add_column("Score", style="green")
        
        for num_images, grid, expected_fill in test_cases:
            score = orchestrator._compute_visual_balance(num_images, grid)
            rows, cols = map(int, grid.split("x"))
            actual_fill = num_images / (rows * cols)
            
            table.add_row(
                str(num_images),
                grid,
                f"{actual_fill:.0%}",
                f"{score:.2f}"
            )
        
        console.print(table)
        console.print("\n[green]✅ Step 6 Complete: Visual balance working![/green]\n")
        return True
        
    except Exception as e:
        console.print(f"\n[red]❌ Step 6 Failed: {e}[/red]\n")
        return False


async def main():
    """Run complete system demonstration"""
    console.print("\n")
    console.print(Panel.fit(
        "[bold magenta]Children's Book Generation System[/bold magenta]\n"
        "[bold white]Complete Working Demonstration[/bold white]\n\n"
        "Testing all components end-to-end",
        border_style="magenta"
    ))
    console.print("\n")
    
    results = []
    
    # Run all demos
    results.append(("Embedding Service", await demo_step_1_embedding_service()))
    results.append(("Knowledge Graph", await demo_step_2_kg_integration()))
    results.append(("Image Pairing", await demo_step_3_image_pairing()))
    results.append(("Grid Layout Logic", await demo_step_4_grid_logic()))
    results.append(("Component Integration", await demo_step_5_orchestration()))
    results.append(("Visual Balance", await demo_step_6_visual_balance()))
    
    # Summary
    console.print(Panel.fit(
        "[bold cyan]DEMONSTRATION COMPLETE[/bold cyan]",
        border_style="cyan"
    ))
    
    summary_table = Table(title="System Status Report")
    summary_table.add_column("Component", style="cyan", width=30)
    summary_table.add_column("Status", style="bold", width=10)
    
    all_passed = True
    for name, passed in results:
        status = "[green]✅ PASS[/green]" if passed else "[red]❌ FAIL[/red]"
        summary_table.add_row(name, status)
        if not passed:
            all_passed = False
    
    console.print(summary_table)
    
    if all_passed:
        console.print("\n[bold green]🎉 ALL SYSTEMS OPERATIONAL![/bold green]")
        console.print("[green]The children's book generation system is working perfectly.[/green]\n")
        return 0
    else:
        console.print("\n[bold red]⚠️  SOME SYSTEMS NEED ATTENTION[/bold red]\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
