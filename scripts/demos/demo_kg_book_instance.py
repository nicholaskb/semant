#!/usr/bin/env python3
"""
Demonstrate Knowledge Graph instance data for book illustrations.
This script populates sample data and then queries it in the same session
to show the actual structure.
"""

import asyncio
from datetime import datetime
from kg.models.graph_manager import KnowledgeGraphManager
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

console = Console()

async def demonstrate_kg_book_data():
    """Populate and query book data in a single session."""
    
    kg = KnowledgeGraphManager()
    await kg.initialize()
    
    console.print(Panel.fit(
        "[bold cyan]📚 Knowledge Graph Book Instance Data Demo[/bold cyan]\n"
        "Showing how Midjourney book illustrations are stored",
        border_style="cyan"
    ))
    
    # ========== POPULATE DATA ==========
    console.print("\n[bold]STEP 1: Populating Sample Data[/bold]\n")
    
    workflow_id = "book_demo_2025"
    workflow_subject = f"http://example.org/book/{workflow_id}"
    
    # Add book workflow
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
    
    # Add Page 1 illustration
    page1_subject = f"http://example.org/book/{workflow_id}/page_1"
    
    triples_added = []
    
    # Type
    t1 = (page1_subject, "rdf:type", "schema:ImageObject")
    await kg.add_triple(
        subject=page1_subject,
        predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        object="http://schema.org/ImageObject"
    )
    triples_added.append(t1)
    
    # Title
    t2 = (page1_subject, "dc:title", "Page 1: Meet Quacky McWaddles")
    await kg.add_triple(
        subject=page1_subject,
        predicate="http://purl.org/dc/terms/title",
        object="Page 1: Meet Quacky McWaddles"
    )
    triples_added.append(t2)
    
    # Prompt
    t3 = (page1_subject, "schema:description", "Children's book watercolor...")
    await kg.add_triple(
        subject=page1_subject,
        predicate="http://schema.org/description",
        object="Children's book watercolor illustration of a cute yellow duckling"
    )
    triples_added.append(t3)
    
    # Midjourney URL
    t4 = (page1_subject, "schema:url", "https://cdn.midjourney.com/.../page1.png")
    await kg.add_triple(
        subject=page1_subject,
        predicate="http://schema.org/url",
        object="https://cdn.midjourney.com/12345/page1.png"
    )
    triples_added.append(t4)
    
    # GCS URL
    t5 = (page1_subject, "schema:contentUrl", "https://storage.googleapis.com/.../page_1.png")
    await kg.add_triple(
        subject=page1_subject,
        predicate="http://schema.org/contentUrl",
        object="https://storage.googleapis.com/bahroo_public/book/page_1.png"
    )
    triples_added.append(t5)
    
    # Job ID
    t6 = (page1_subject, "mj:jobId", "job-001")
    await kg.add_triple(
        subject=page1_subject,
        predicate="http://example.org/midjourney/jobId",
        object="job-001-abc-def"
    )
    triples_added.append(t6)
    
    # Task ID
    t7 = (page1_subject, "mj:taskId", "task-001")
    await kg.add_triple(
        subject=page1_subject,
        predicate="http://example.org/midjourney/taskId",
        object="task-001-xyz"
    )
    triples_added.append(t7)
    
    # Created
    t8 = (page1_subject, "dc:created", "2025-09-17T22:30:00Z")
    await kg.add_triple(
        subject=page1_subject,
        predicate="http://purl.org/dc/terms/created",
        object=datetime.now().isoformat()
    )
    triples_added.append(t8)
    
    # Part of workflow
    t9 = (page1_subject, "dc:isPartOf", workflow_subject)
    await kg.add_triple(
        subject=page1_subject,
        predicate="http://purl.org/dc/terms/isPartOf",
        object=workflow_subject
    )
    triples_added.append(t9)
    
    # Display triples added
    table = Table(title="Sample Triples Added for Page 1")
    table.add_column("Subject", style="cyan", no_wrap=False)
    table.add_column("Predicate", style="yellow")
    table.add_column("Object", style="green", no_wrap=False)
    
    for triple in triples_added:
        subj = triple[0].replace("http://example.org/book/book_demo_2025/", "")
        table.add_row(subj, triple[1], triple[2])
    
    console.print(table)
    
    # ========== QUERY DATA ==========
    console.print("\n[bold]STEP 2: SPARQL Queries[/bold]\n")
    
    # Query 1: Get all triples for this page
    query1 = f"""
    SELECT ?predicate ?object
    WHERE {{
        <{page1_subject}> ?predicate ?object .
    }}
    """
    
    console.print("[cyan]Query 1: All triples for Page 1[/cyan]")
    console.print(Syntax(query1.strip(), "sparql", theme="monokai"))
    
    results1 = await kg.query_graph(query1)
    
    if results1:
        console.print(f"\n[green]Results ({len(results1)} triples):[/green]")
        result_table = Table()
        result_table.add_column("Predicate", style="yellow")
        result_table.add_column("Object", style="green")
        
        for result in results1:
            pred = str(result.get('predicate', ''))
            pred = pred.replace('http://schema.org/', 'schema:')
            pred = pred.replace('http://purl.org/dc/terms/', 'dc:')
            pred = pred.replace('http://example.org/midjourney/', 'mj:')
            pred = pred.replace('http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'rdf:')
            
            obj = str(result.get('object', ''))
            if len(obj) > 50:
                obj = obj[:47] + "..."
            
            result_table.add_row(pred, obj)
        
        console.print(result_table)
    
    # Query 2: Get GCS URL for the page
    query2 = f"""
    PREFIX schema: <http://schema.org/>
    
    SELECT ?gcs_url
    WHERE {{
        <{page1_subject}> schema:contentUrl ?gcs_url .
    }}
    """
    
    console.print("\n[cyan]Query 2: Get GCS URL[/cyan]")
    console.print(Syntax(query2.strip(), "sparql", theme="monokai"))
    
    results2 = await kg.query_graph(query2)
    if results2:
        gcs_url = results2[0].get('gcs_url', '')
        console.print(f"\n[green]GCS URL:[/green] {gcs_url}")
    
    # Query 3: Get all pages in workflow
    query3 = f"""
    PREFIX dc: <http://purl.org/dc/terms/>
    PREFIX schema: <http://schema.org/>
    
    SELECT ?page ?title
    WHERE {{
        ?page dc:isPartOf <{workflow_subject}> .
        OPTIONAL {{ ?page dc:title ?title }}
    }}
    """
    
    console.print("\n[cyan]Query 3: All pages in workflow[/cyan]")
    console.print(Syntax(query3.strip(), "sparql", theme="monokai"))
    
    results3 = await kg.query_graph(query3)
    if results3:
        console.print(f"\n[green]Pages in workflow:[/green]")
        for result in results3:
            page = result.get('page', '').split('/')[-1]
            title = result.get('title', 'N/A')
            console.print(f"  • {page}: {title}")
    
    # ========== SUMMARY ==========
    console.print("\n" + "="*70)
    console.print(Panel(
        "[bold green]Knowledge Graph Structure Summary[/bold green]\n\n"
        "Each illustration page is stored as:\n"
        "• Subject: http://example.org/book/{workflow_id}/page_{num}\n"
        "• Type: schema:ImageObject\n"
        "• Properties:\n"
        "  - dc:title (page title)\n"
        "  - schema:description (Midjourney prompt)\n"
        "  - schema:url (Midjourney CDN URL)\n"
        "  - schema:contentUrl (GCS public URL)\n"
        "  - mj:jobId (job identifier)\n"
        "  - mj:taskId (task identifier)\n"
        "  - dc:created (timestamp)\n"
        "  - dc:isPartOf (link to workflow)",
        border_style="green"
    ))
    
    await kg.shutdown()


if __name__ == "__main__":
    asyncio.run(demonstrate_kg_book_data())
