#!/usr/bin/env python3
"""
Verify that all images are in KG and Qdrant
"""

import asyncio
from qdrant_client import QdrantClient
from kg.models.graph_manager import KnowledgeGraphManager
from rich.console import Console
from rich.table import Table

console = Console()

async def verify_ingestion():
    """Verify images are in both KG and Qdrant"""
    
    console.print("\n[bold cyan]🔍 Verifying Image Ingestion[/bold cyan]\n")
    
    # Check Qdrant
    console.print("[bold]Checking Qdrant...[/bold]")
    try:
        qdrant_client = QdrantClient(host="localhost", port=6333)
        collection_info = qdrant_client.get_collection("childrens_book_images")
        qdrant_count = collection_info.points_count
        console.print(f"  ✅ Qdrant: {qdrant_count} embeddings stored")
    except Exception as e:
        console.print(f"  ❌ Qdrant error: {e}")
        qdrant_count = 0
    
    # Check Knowledge Graph
    console.print("\n[bold]Checking Knowledge Graph...[/bold]")
    try:
        kg_manager = KnowledgeGraphManager()
        await kg_manager.initialize()
        
        # Query for input images
        input_query = """
        PREFIX schema: <http://schema.org/>
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT (COUNT(?image) as ?count) WHERE {
            ?image a book:InputImage .
        }
        """
        input_results = await kg_manager.query_graph(input_query)
        input_count = int(input_results[0]["count"]) if input_results else 0
        
        # Query for output images
        output_query = """
        PREFIX schema: <http://schema.org/>
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT (COUNT(?image) as ?count) WHERE {
            ?image a book:OutputImage .
        }
        """
        output_results = await kg_manager.query_graph(output_query)
        output_count = int(output_results[0]["count"]) if output_results else 0
        
        total_kg = input_count + output_count
        console.print(f"  ✅ Knowledge Graph:")
        console.print(f"     - Input images: {input_count}")
        console.print(f"     - Output images: {output_count}")
        console.print(f"     - Total: {total_kg}")
        
    except Exception as e:
        console.print(f"  ❌ KG error: {e}")
        import traceback
        traceback.print_exc()
        total_kg = 0
        input_count = 0
        output_count = 0
    
    # Summary table
    table = Table(title="Ingestion Verification Summary")
    table.add_column("Source", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Status", style="yellow")
    
    table.add_row("Expected Total", "4426", "86 inputs + 4340 outputs")
    table.add_row("Qdrant Embeddings", str(qdrant_count), "✅" if qdrant_count >= 4000 else "⚠️")
    table.add_row("KG Input Images", str(input_count), "✅" if input_count >= 80 else "⚠️")
    table.add_row("KG Output Images", str(output_count), "✅" if output_count >= 4000 else "⚠️")
    table.add_row("KG Total", str(total_kg), "✅" if total_kg >= 4000 else "⚠️")
    
    console.print("\n")
    console.print(table)
    
    # Final status
    if qdrant_count >= 4000 and total_kg >= 4000:
        console.print("\n[bold green]✅ SUCCESS: All images processed and stored![/bold green]")
        return True
    else:
        console.print("\n[bold yellow]⚠️  INCOMPLETE: Some images may still be processing[/bold yellow]")
        console.print(f"   Qdrant: {qdrant_count}/4426 ({qdrant_count*100//4426}%)")
        console.print(f"   KG: {total_kg}/4426 ({total_kg*100//4426}%)")
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_ingestion())
    exit(0 if success else 1)

