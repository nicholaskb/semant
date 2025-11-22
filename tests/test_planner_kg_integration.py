#!/usr/bin/env python3
"""Test script for Planner Knowledge Graph integration."""

import asyncio
import requests
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from datetime import datetime

console = Console()

def test_create_plan():
    """Create a plan and store it in the Knowledge Graph."""
    console.print("\n[bold cyan]1. Creating a Midjourney Theme Plan...[/bold cyan]")
    
    plan_request = {
        "theme": "Marvel superheroes image generation workflow",
        "context": {
            "count": 5,
            "image_urls": ["https://example.com/face1.jpg", "https://example.com/face2.jpg"],
            "requirements": "High quality cinematic portraits with dramatic lighting",
            "version": "v7",
            "process_mode": "fast"
        }
    }
    
    console.print(f"[dim]Theme:[/dim] {plan_request['theme']}")
    console.print(f"[dim]Context:[/dim]")
    console.print(json.dumps(plan_request['context'], indent=2))
    
    response = requests.post(
        "http://localhost:8000/api/planner/create-plan",
        json=plan_request
    )
    
    if response.status_code == 200:
        plan = response.json()
        
        # Display plan info
        info_panel = Panel(
            f"Plan ID: {plan['id']}\n"
            f"Created: {plan['created_at']}\n"
            f"Steps: {len(plan.get('steps', []))}\n"
            f"KG Stored: {plan.get('kg_stored', False)}",
            title="[bold green]Plan Created Successfully[/bold green]",
            border_style="green"
        )
        console.print(info_panel)
        
        # Display steps
        if plan.get('steps'):
            console.print("\n[bold]Plan Steps:[/bold]")
            for step in plan['steps']:
                console.print(f"\n[cyan]Step {step['step']}:[/cyan] {step['action']}")
                console.print(f"  Description: {step['description']}")
                console.print(f"  Agent: {step['agent']}")
                if 'input' in step:
                    console.print(f"  Input: {step['input']}")
                console.print(f"  Output: {step['output']}")
        
        return plan['id']
    else:
        console.print(f"[bold red]Error:[/bold red] {response.status_code} - {response.text}")
        return None

def test_retrieve_plan(plan_id: str):
    """Retrieve a plan from the Knowledge Graph."""
    console.print(f"\n[bold cyan]2. Retrieving Plan {plan_id}...[/bold cyan]")
    
    response = requests.get(f"http://localhost:8000/api/planner/get-plan/{plan_id}")
    
    if response.status_code == 200:
        plan = response.json()
        
        # Display retrieved plan
        panel = Panel(
            json.dumps(plan, indent=2),
            title="[bold green]Retrieved Plan[/bold green]",
            border_style="green"
        )
        console.print(panel)
        return True
    else:
        console.print(f"[bold red]Error:[/bold red] {response.status_code} - {response.text}")
        return False

def test_list_plans(theme_filter: str = None):
    """List all plans in the Knowledge Graph."""
    console.print("\n[bold cyan]3. Listing Plans in Knowledge Graph...[/bold cyan]")
    
    params = {"theme_filter": theme_filter} if theme_filter else {}
    response = requests.get("http://localhost:8000/api/planner/list-plans", params=params)
    
    if response.status_code == 200:
        data = response.json()
        plans = data.get("plans", [])
        
        if plans:
            # Create table
            table = Table(title=f"Plans in Knowledge Graph ({data['count']} total)")
            table.add_column("ID", style="cyan")
            table.add_column("Theme", style="green")
            table.add_column("Created At", style="yellow")
            table.add_column("Status", style="magenta")
            
            for plan in plans:
                table.add_row(
                    plan['id'],
                    plan['theme'][:50] + "..." if len(plan['theme']) > 50 else plan['theme'],
                    plan['created_at'],
                    plan['status']
                )
            
            console.print(table)
        else:
            console.print("[yellow]No plans found in Knowledge Graph[/yellow]")
        
        return plans
    else:
        console.print(f"[bold red]Error:[/bold red] {response.status_code} - {response.text}")
        return []

def test_execute_step(plan_id: str, step_number: int):
    """Execute a step from a plan."""
    console.print(f"\n[bold cyan]4. Executing Step {step_number} of Plan {plan_id}...[/bold cyan]")
    
    response = requests.post(
        "http://localhost:8000/api/planner/execute-step",
        json={"plan_id": plan_id, "step_number": step_number}
    )
    
    if response.status_code == 200:
        result = response.json()
        
        panel = Panel(
            f"Action: {result['action']}\n"
            f"Status: {result['status']}\n"
            f"Timestamp: {result['timestamp']}",
            title="[bold green]Step Executed[/bold green]",
            border_style="green"
        )
        console.print(panel)
        return True
    else:
        console.print(f"[bold red]Error:[/bold red] {response.status_code} - {response.text}")
        return False

def test_sparql_query():
    """Demonstrate direct SPARQL query for plans."""
    console.print("\n[bold cyan]5. Direct SPARQL Query for Plans...[/bold cyan]")
    
    # This would need a SPARQL endpoint if available
    sparql_query = """
    PREFIX plan: <http://example.org/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?plan ?theme ?createdAt
    WHERE {
        ?plan rdf:type plan:Plan .
        ?plan plan:hasTheme ?theme .
        ?plan plan:createdAt ?createdAt .
    }
    ORDER BY DESC(?createdAt)
    LIMIT 5
    """
    
    syntax = Syntax(sparql_query, "sparql", theme="monokai")
    console.print(Panel(syntax, title="Sample SPARQL Query", border_style="dim"))
    
    console.print("[yellow]Note: Direct SPARQL queries require a SPARQL endpoint to be configured[/yellow]")

def main():
    """Run all tests."""
    console.print(Panel.fit(
        "[bold]Planner Knowledge Graph Integration Test[/bold]\n"
        "This demonstrates storing and retrieving plans in the KG",
        border_style="cyan"
    ))
    
    # Check planner status first
    response = requests.get("http://localhost:8000/api/planner-status")
    if response.status_code != 200 or not response.json().get("planner_available"):
        console.print("[bold red]❌ Planner is not available. Please start the server first.[/bold red]")
        return
    
    console.print("[bold green]✅ Planner is available[/bold green]")
    
    # Test 1: Create a plan
    plan_id = test_create_plan()
    
    if plan_id:
        # Test 2: Retrieve the plan
        test_retrieve_plan(plan_id)
        
        # Test 3: Execute first step
        test_execute_step(plan_id, 1)
    
    # Test 4: List all plans
    test_list_plans()
    
    # Test 5: List filtered plans
    console.print("\n[bold cyan]Filtering plans by 'image' theme...[/bold cyan]")
    test_list_plans("image")
    
    # Show SPARQL example
    test_sparql_query()
    
    console.print("\n[bold green]✅ Test Complete![/bold green]")
    
    console.print("\n[bold]Key Capabilities Demonstrated:[/bold]")
    console.print("• Create structured plans from themes")
    console.print("• Store plans as RDF triples in Knowledge Graph")
    console.print("• Retrieve plans by ID")
    console.print("• List and filter plans")
    console.print("• Execute plan steps (triggers agent actions)")
    console.print("• Plans are queryable via SPARQL")
    
    console.print("\n[bold]Use Cases:[/bold]")
    console.print("• Store reusable workflows in KG")
    console.print("• Track plan execution history")
    console.print("• Query plans by theme, agent, or status")
    console.print("• Build complex multi-agent orchestrations")
    console.print("• Version and audit workflow execution")

if __name__ == "__main__":
    main()

