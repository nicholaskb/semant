#!/usr/bin/env python3
"""
Populate the Knowledge Graph with sample book illustration data
to demonstrate SPARQL queries
"""

import asyncio
from datetime import datetime
from kg.models.graph_manager import KnowledgeGraphManager
from rich.console import Console
from rich.panel import Panel

console = Console()

async def populate_sample_data():
    """Add sample book illustration data to the Knowledge Graph."""
    
    kg = KnowledgeGraphManager()
    await kg.initialize()
    
    console.print(Panel.fit(
        "[bold cyan]📝 Populating Knowledge Graph with Sample Book Data[/bold cyan]",
        border_style="cyan"
    ))
    
    workflow_id = "book_sample_demo_2025"
    
    # Sample data for 3 pages
    pages_data = [
        {
            "page_num": 1,
            "title": "Meet Quacky McWaddles",
            "prompt": "Children's book watercolor illustration of a cute yellow duckling with comically oversized orange webbed feet",
            "midjourney_url": "https://cdn.midjourney.com/12345678-1234-1234-1234-123456789012/page1.png",
            "gcs_url": "https://storage.googleapis.com/bahroo_public/book_illustrations/sample/page_1.png",
            "job_id": "sample-job-001",
            "task_id": "sample-task-001"
        },
        {
            "page_num": 7,
            "title": "The Tangled Mess",
            "prompt": "Children's book watercolor of yellow duckling tangled in green reeds and grass",
            "midjourney_url": "https://cdn.midjourney.com/87654321-4321-4321-4321-210987654321/page7.png",
            "gcs_url": "https://storage.googleapis.com/bahroo_public/book_illustrations/sample/page_7.png",
            "job_id": "sample-job-007",
            "task_id": "sample-task-007"
        },
        {
            "page_num": 12,
            "title": "The Happy Ending",
            "prompt": "Children's book watercolor celebration scene, multiple ducklings doing the Waddle Hop dance",
            "midjourney_url": "https://cdn.midjourney.com/abcdefgh-abcd-abcd-abcd-abcdefghijkl/page12.png",
            "gcs_url": "https://storage.googleapis.com/bahroo_public/book_illustrations/sample/page_12.png",
            "job_id": "sample-job-012",
            "task_id": "sample-task-012"
        }
    ]
    
    # First, create the workflow/book entity
    workflow_subject = f"http://example.org/book/{workflow_id}"
    
    await kg.add_triple(
        subject=workflow_subject,
        predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        object="http://schema.org/Book"
    )
    
    await kg.add_triple(
        subject=workflow_subject,
        predicate="http://purl.org/dc/terms/title",
        object="Quacky McWaddles' Big Adventure"
    )
    
    await kg.add_triple(
        subject=workflow_subject,
        predicate="http://purl.org/dc/terms/created",
        object=datetime.now().isoformat()
    )
    
    console.print(f"[green]✓ Created workflow: {workflow_id}[/green]")
    
    # Add data for each page
    for page_data in pages_data:
        page_num = page_data["page_num"]
        subject = f"http://example.org/book/{workflow_id}/page_{page_num}"
        
        console.print(f"\nAdding Page {page_num}: {page_data['title']}")
        
        # Type
        await kg.add_triple(
            subject=subject,
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            object="http://schema.org/ImageObject"
        )
        
        # Title
        await kg.add_triple(
            subject=subject,
            predicate="http://purl.org/dc/terms/title",
            object=f"Page {page_num}: {page_data['title']}"
        )
        
        # Prompt/Description
        await kg.add_triple(
            subject=subject,
            predicate="http://schema.org/description",
            object=page_data["prompt"]
        )
        
        # Midjourney URL
        await kg.add_triple(
            subject=subject,
            predicate="http://schema.org/url",
            object=page_data["midjourney_url"]
        )
        
        # GCS URL
        await kg.add_triple(
            subject=subject,
            predicate="http://schema.org/contentUrl",
            object=page_data["gcs_url"]
        )
        
        # Job ID
        await kg.add_triple(
            subject=subject,
            predicate="http://example.org/midjourney/jobId",
            object=page_data["job_id"]
        )
        
        # Task ID
        await kg.add_triple(
            subject=subject,
            predicate="http://example.org/midjourney/taskId",
            object=page_data["task_id"]
        )
        
        # Created timestamp
        await kg.add_triple(
            subject=subject,
            predicate="http://purl.org/dc/terms/created",
            object=datetime.now().isoformat()
        )
        
        # Link to workflow
        await kg.add_triple(
            subject=subject,
            predicate="http://purl.org/dc/terms/isPartOf",
            object=workflow_subject
        )
        
        console.print(f"  [dim]✓ Added 9 triples for page {page_num}[/dim]")
    
    # Add some metadata about the generation process
    process_subject = f"http://example.org/process/{workflow_id}_generation"
    
    await kg.add_triple(
        subject=process_subject,
        predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        object="http://example.org/midjourney/GenerationProcess"
    )
    
    await kg.add_triple(
        subject=process_subject,
        predicate="http://example.org/midjourney/model",
        object="V_6"
    )
    
    await kg.add_triple(
        subject=process_subject,
        predicate="http://example.org/midjourney/quality",
        object="1"
    )
    
    await kg.add_triple(
        subject=process_subject,
        predicate="http://example.org/midjourney/stylize",
        object="750"
    )
    
    await kg.add_triple(
        subject=process_subject,
        predicate="http://schema.org/agent",
        object="IllustrationWorkflowAgent"
    )
    
    console.print(f"\n[green]✓ Added generation process metadata[/green]")
    
    # Query to verify
    console.print("\n[bold]Verifying data with SPARQL query:[/bold]")
    
    query = f"""
    PREFIX schema: <http://schema.org/>
    PREFIX dc: <http://purl.org/dc/terms/>
    
    SELECT ?page ?title ?gcs_url
    WHERE {{
        ?page dc:isPartOf <{workflow_subject}> .
        ?page dc:title ?title .
        ?page schema:contentUrl ?gcs_url .
    }}
    ORDER BY ?page
    """
    
    results = await kg.query_graph(query)
    
    if results:
        console.print(f"\n[cyan]Found {len(results)} pages in Knowledge Graph:[/cyan]")
        for result in results:
            title = result.get('title', '')
            gcs = result.get('gcs_url', '')
            console.print(f"  • {title}")
            console.print(f"    [dim]{gcs}[/dim]")
    
    # Count total triples
    count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
    count_result = await kg.query_graph(count_query)
    total = count_result[0].get('count', 0) if count_result else 0
    
    console.print(f"\n[bold green]✅ Successfully populated Knowledge Graph[/bold green]")
    console.print(f"[cyan]Total triples: {total}[/cyan]")
    console.print(f"[cyan]Workflow ID: {workflow_id}[/cyan]")
    
    await kg.shutdown()
    
    return workflow_id


if __name__ == "__main__":
    workflow_id = asyncio.run(populate_sample_data())
    print(f"\n📊 You can now query this data using workflow ID: {workflow_id}")
