#!/usr/bin/env python3
"""
Query the Knowledge Graph for book illustration instances
"""

import asyncio
from kg.models.graph_manager import KnowledgeGraphManager
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

console = Console()

async def query_book_illustrations():
    """Query all book illustrations in the Knowledge Graph."""
    
    kg = KnowledgeGraphManager()
    await kg.initialize()
    
    console.print(Panel.fit(
        "[bold cyan]📊 Querying Knowledge Graph for Book Illustrations[/bold cyan]",
        border_style="cyan"
    ))
    
    # Query 1: Find all ImageObject instances
    query1 = """
    PREFIX schema: <http://schema.org/>
    PREFIX dc: <http://purl.org/dc/terms/>
    PREFIX mj: <http://example.org/midjourney/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?subject ?predicate ?object
    WHERE {
        ?subject rdf:type schema:ImageObject .
        ?subject ?predicate ?object .
    }
    ORDER BY ?subject ?predicate
    LIMIT 100
    """
    
    console.print("\n[bold]Query 1: All Book Illustration Triples[/bold]")
    console.print(Syntax(query1, "sparql", theme="monokai"))
    
    try:
        results1 = await kg.query_graph(query1)
        
        if results1:
            console.print(f"\n[green]Found {len(results1)} triples for ImageObjects[/green]\n")
            
            # Create table for results
            table = Table(title="Book Illustration Data in Knowledge Graph")
            table.add_column("Subject", style="cyan", no_wrap=False)
            table.add_column("Predicate", style="yellow")
            table.add_column("Object", style="green", no_wrap=False)
            
            for result in results1[:20]:  # Show first 20
                subject = str(result.get('subject', '')).replace('http://example.org/', '...')
                predicate = str(result.get('predicate', '')).replace('http://schema.org/', 'schema:').replace('http://purl.org/dc/terms/', 'dc:')
                obj = str(result.get('object', ''))
                if len(obj) > 50:
                    obj = obj[:47] + "..."
                table.add_row(subject, predicate, obj)
            
            console.print(table)
        else:
            console.print("[yellow]No ImageObject instances found in Knowledge Graph[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Error executing query 1: {e}[/red]")
    
    # Query 2: Find all book workflows
    query2 = """
    PREFIX dc: <http://purl.org/dc/terms/>
    
    SELECT DISTINCT ?workflow
    WHERE {
        ?page dc:isPartOf ?workflow .
        FILTER(CONTAINS(STR(?workflow), "book"))
    }
    """
    
    console.print("\n[bold]Query 2: Book Workflows[/bold]")
    console.print(Syntax(query2, "sparql", theme="monokai"))
    
    try:
        results2 = await kg.query_graph(query2)
        
        if results2:
            console.print(f"\n[green]Found {len(results2)} book workflows[/green]")
            for result in results2:
                workflow = result.get('workflow', '')
                console.print(f"  • {workflow}")
        else:
            console.print("[yellow]No book workflows found[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Error executing query 2: {e}[/red]")
    
    # Query 3: Find any Midjourney-related data
    query3 = """
    SELECT ?subject ?predicate ?object
    WHERE {
        ?subject ?predicate ?object .
        FILTER(
            CONTAINS(STR(?subject), "midjourney") || 
            CONTAINS(STR(?predicate), "midjourney") ||
            CONTAINS(STR(?object), "midjourney") ||
            CONTAINS(STR(?subject), "book") ||
            CONTAINS(STR(?object), "duckling") ||
            CONTAINS(STR(?object), "Quacky")
        )
    }
    LIMIT 50
    """
    
    console.print("\n[bold]Query 3: Any Midjourney or Book-related Data[/bold]")
    console.print(Syntax(query3, "sparql", theme="monokai"))
    
    try:
        results3 = await kg.query_graph(query3)
        
        if results3:
            console.print(f"\n[green]Found {len(results3)} related triples[/green]\n")
            
            # Group by subject
            by_subject = {}
            for result in results3:
                subj = result.get('subject', '')
                if subj not in by_subject:
                    by_subject[subj] = []
                by_subject[subj].append({
                    'predicate': result.get('predicate', ''),
                    'object': result.get('object', '')
                })
            
            for subject, triples in list(by_subject.items())[:5]:  # Show first 5 subjects
                console.print(f"\n[cyan]Subject: {subject}[/cyan]")
                for triple in triples:
                    pred = triple['predicate'].replace('http://schema.org/', 'schema:').replace('http://purl.org/dc/terms/', 'dc:')
                    obj = triple['object']
                    if len(str(obj)) > 80:
                        obj = str(obj)[:77] + "..."
                    console.print(f"  {pred}: {obj}")
        else:
            console.print("[yellow]No Midjourney or book-related data found[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Error executing query 3: {e}[/red]")
    
    # Query 4: Count all triples
    query4 = """
    SELECT (COUNT(*) as ?count)
    WHERE {
        ?s ?p ?o
    }
    """
    
    console.print("\n[bold]Query 4: Total Triple Count[/bold]")
    
    try:
        results4 = await kg.query_graph(query4)
        if results4:
            count = results4[0].get('count', 0)
            console.print(f"[cyan]Total triples in Knowledge Graph: {count}[/cyan]")
    except Exception as e:
        console.print(f"[red]Error counting triples: {e}[/red]")
    
    await kg.shutdown()


if __name__ == "__main__":
    asyncio.run(query_book_illustrations())
