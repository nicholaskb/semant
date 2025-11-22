#!/usr/bin/env python3
"""
Examples of SPARQL queries for plans stored in the Knowledge Graph.
This script demonstrates various ways to query plans using SPARQL.
"""

import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from kg.models.graph_manager import KnowledgeGraphManager
from agents.domain.planner_agent import PlannerAgent
from agents.core.agent_registry import AgentRegistry
import json

console = Console()

# Example SPARQL queries for plans
SPARQL_QUERIES = {
    "all_plans": """
        PREFIX plan: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?plan ?theme ?createdAt ?status
        WHERE {
            ?plan rdf:type plan:Plan .
            ?plan plan:hasTheme ?theme .
            ?plan plan:createdAt ?createdAt .
            ?plan plan:status ?status .
        }
        ORDER BY DESC(?createdAt)
        LIMIT 10
    """,
    
    "plans_by_theme": """
        PREFIX plan: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?plan ?theme ?createdAt
        WHERE {
            ?plan rdf:type plan:Plan .
            ?plan plan:hasTheme ?theme .
            ?plan plan:createdAt ?createdAt .
            FILTER(CONTAINS(LCASE(?theme), "marvel"))
        }
        ORDER BY DESC(?createdAt)
    """,
    
    "plan_details": """
        PREFIX plan: <http://example.org/ontology#>
        
        SELECT ?predicate ?object
        WHERE {
            <http://example.org/plan/plan_20250916_233431> ?predicate ?object .
        }
    """,
    
    "plan_steps": """
        PREFIX plan: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?step ?stepNumber ?action ?description ?agent
        WHERE {
            ?step rdf:type plan:PlanStep .
            ?step plan:belongsToPlan <http://example.org/plan/plan_20250916_233431> .
            ?step plan:stepNumber ?stepNumber .
            ?step plan:action ?action .
            ?step plan:description ?description .
            ?step plan:assignedAgent ?agent .
        }
        ORDER BY ?stepNumber
    """,
    
    "plans_using_agent": """
        PREFIX plan: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?plan ?theme
        WHERE {
            ?plan rdf:type plan:Plan .
            ?plan plan:hasTheme ?theme .
            ?step plan:belongsToPlan ?plan .
            ?step plan:assignedAgent "critic_agent" .
        }
    """,
    
    "plans_created_today": """
        PREFIX plan: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT ?plan ?theme ?createdAt
        WHERE {
            ?plan rdf:type plan:Plan .
            ?plan plan:hasTheme ?theme .
            ?plan plan:createdAt ?createdAt .
            FILTER(?createdAt >= "2025-09-16T00:00:00"^^xsd:dateTime)
        }
        ORDER BY DESC(?createdAt)
    """,
    
    "count_plans": """
        PREFIX plan: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT (COUNT(?plan) as ?count)
        WHERE {
            ?plan rdf:type plan:Plan .
        }
    """,
    
    "plans_with_image_theme": """
        PREFIX plan: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?plan ?theme
        WHERE {
            ?plan rdf:type plan:Plan .
            ?plan plan:hasTheme ?theme .
            FILTER(CONTAINS(LCASE(?theme), "image") || 
                   CONTAINS(LCASE(?theme), "midjourney") ||
                   CONTAINS(LCASE(?theme), "portrait"))
        }
    """,
    
    "plan_status_distribution": """
        PREFIX plan: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?status (COUNT(?plan) as ?count)
        WHERE {
            ?plan rdf:type plan:Plan .
            ?plan plan:status ?status .
        }
        GROUP BY ?status
        ORDER BY DESC(?count)
    """
}

async def execute_sparql_query(kg_manager, query_name, query):
    """Execute a SPARQL query and display results."""
    console.print(f"\n[bold cyan]{query_name}:[/bold cyan]")
    
    # Display the query
    syntax = Syntax(query, "sparql", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="SPARQL Query", border_style="dim"))
    
    try:
        # Execute the query
        results = await kg_manager.query_graph(query)
        
        if results:
            # Create a table for results
            if results[0]:  # Check if there are keys
                table = Table(title=f"Results ({len(results)} rows)")
                
                # Add columns based on first result
                for key in results[0].keys():
                    table.add_column(key, style="cyan")
                
                # Add rows
                for result in results:
                    row_values = []
                    for key in results[0].keys():
                        value = result.get(key, "")
                        # Truncate long values
                        if len(str(value)) > 50:
                            value = str(value)[:47] + "..."
                        row_values.append(str(value))
                    table.add_row(*row_values)
                
                console.print(table)
            else:
                console.print("[yellow]Query returned empty results[/yellow]")
        else:
            console.print("[yellow]No results found[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error executing query: {e}[/red]")

async def main():
    """Demonstrate SPARQL queries for plans."""
    console.print(Panel.fit(
        "[bold]SPARQL Query Examples for Plans[/bold]\n"
        "Demonstrating how to query plans stored in the Knowledge Graph",
        border_style="cyan"
    ))
    
    # Initialize Knowledge Graph
    console.print("\n[bold]Initializing Knowledge Graph...[/bold]")
    kg_manager = KnowledgeGraphManager()
    
    try:
        await kg_manager.initialize()
        console.print("[green]✅ Knowledge Graph initialized[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize KG: {e}[/red]")
        return
    
    # Execute example queries
    console.print("\n[bold]Executing SPARQL Queries:[/bold]")
    
    # Query 1: Get all plans
    await execute_sparql_query(kg_manager, "1. Get All Plans", SPARQL_QUERIES["all_plans"])
    
    # Query 2: Find Marvel-themed plans
    await execute_sparql_query(kg_manager, "2. Find Marvel-Themed Plans", SPARQL_QUERIES["plans_by_theme"])
    
    # Query 3: Count total plans
    await execute_sparql_query(kg_manager, "3. Count Total Plans", SPARQL_QUERIES["count_plans"])
    
    # Query 4: Get plan status distribution
    await execute_sparql_query(kg_manager, "4. Plan Status Distribution", SPARQL_QUERIES["plan_status_distribution"])
    
    # Query 5: Find image-related plans
    await execute_sparql_query(kg_manager, "5. Image Generation Plans", SPARQL_QUERIES["plans_with_image_theme"])
    
    # Additional tips
    console.print("\n[bold]Tips for Using SPARQL with Plans:[/bold]")
    tips = [
        "• Use PREFIX to shorten URIs (e.g., plan: for http://example.org/ontology#)",
        "• FILTER with CONTAINS for text search in themes",
        "• ORDER BY DESC(?createdAt) for newest plans first",
        "• Use COUNT for aggregations",
        "• JOIN step data with plan data using plan:belongsToPlan",
        "• Use DISTINCT to avoid duplicates",
        "• LIMIT results for performance",
        "• Use OPTIONAL for properties that might not exist"
    ]
    for tip in tips:
        console.print(tip)
    
    console.print("\n[bold]Ways to Execute SPARQL Queries:[/bold]")
    console.print("1. Direct KG query: `await kg_manager.query_graph(sparql)`")
    console.print("2. Via agent: `await agent.query_knowledge_graph({'sparql': query})`")
    console.print("3. Through API endpoint (if available)")
    console.print("4. Using SPARQL endpoint directly (if configured)")
    
    # Show how to construct dynamic queries
    console.print("\n[bold]Example: Dynamic Query Construction[/bold]")
    
    theme_filter = "marvel"
    dynamic_query = f"""
        PREFIX plan: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?plan ?theme
        WHERE {{
            ?plan rdf:type plan:Plan .
            ?plan plan:hasTheme ?theme .
            FILTER(CONTAINS(LCASE(?theme), LCASE("{theme_filter}")))
        }}
        LIMIT 5
    """
    
    syntax = Syntax(dynamic_query, "sparql", theme="monokai")
    console.print(Panel(syntax, title="Dynamic Query Example", border_style="green"))
    
    # Show how to extract plan JSON from results
    console.print("\n[bold]Extracting Full Plan Data:[/bold]")
    
    plan_data_query = """
        PREFIX plan: <http://example.org/ontology#>
        
        SELECT ?planData
        WHERE {
            <http://example.org/plan/plan_20250916_233431> plan:planData ?planData .
        }
    """
    
    try:
        results = await kg_manager.query_graph(plan_data_query)
        if results and results[0].get("planData"):
            plan_json = json.loads(results[0]["planData"])
            console.print("[green]Full plan retrieved and parsed from JSON[/green]")
            console.print(f"Plan ID: {plan_json.get('id')}")
            console.print(f"Steps: {len(plan_json.get('steps', []))}")
    except:
        console.print("[yellow]Note: Run after creating a plan to see data[/yellow]")
    
    console.print("\n[bold green]✅ SPARQL Query Examples Complete![/bold green]")

if __name__ == "__main__":
    asyncio.run(main())

