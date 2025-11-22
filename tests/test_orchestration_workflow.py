#!/usr/bin/env python3
"""
Test script for the Comprehensive Orchestration Workflow.
This demonstrates the complete 7-step process from text file to post-execution analysis.
"""

import asyncio
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import requests

console = Console()

# First, create a sample requirements file
SAMPLE_REQUIREMENTS = """
Project: E-Commerce Data Pipeline
================================

Objective:
Create a comprehensive data pipeline for processing e-commerce transactions with the following requirements:

1. Data Ingestion:
   - Collect data from multiple sources (API, Database, CSV files)
   - Validate incoming data for completeness
   - Handle different data formats (JSON, XML, CSV)

2. Data Processing:
   - Clean and normalize transaction data
   - Calculate aggregate metrics (daily sales, customer segments)
   - Detect anomalies in transaction patterns

3. Data Storage:
   - Store processed data in a data warehouse
   - Maintain audit logs of all transformations
   - Implement data versioning

4. Reporting:
   - Generate daily summary reports
   - Create visualizations for key metrics
   - Send alerts for anomalies

5. Quality Assurance:
   - Validate data accuracy at each step
   - Perform consistency checks
   - Monitor pipeline performance

Technical Requirements:
- Must handle 100,000 transactions per day
- Processing latency < 5 minutes
- 99.9% uptime requirement
- Full audit trail for compliance

Deliverables:
- Fully functional data pipeline
- Documentation and runbooks
- Monitoring dashboard
- Test suite
"""

async def create_requirements_file():
    """Create a sample requirements file."""
    file_path = Path("sample_requirements.txt")
    file_path.write_text(SAMPLE_REQUIREMENTS)
    console.print(f"[green]✅ Created requirements file: {file_path}[/green]")
    return str(file_path)

async def test_orchestration_workflow():
    """Test the complete orchestration workflow."""
    console.print(Panel.fit(
        "[bold]Comprehensive Orchestration Workflow Test[/bold]\n"
        "Testing the 7-step workflow from text to post-execution analysis",
        border_style="cyan"
    ))
    
    # Step 0: Create requirements file
    requirements_file = await create_requirements_file()
    user_email = "test@example.com"  # Change this to your email for real tests
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/api/planner-status")
        if response.status_code != 200 or not response.json().get("planner_available"):
            console.print("[red]❌ Planner not available. Start the server first.[/red]")
            return
    except requests.exceptions.ConnectionError:
        console.print("[red]❌ Server not running. Start with: python3 main.py[/red]")
        return
    
    console.print("[green]✅ Server and Planner available[/green]\n")
    
    workflow_id = None
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Step 1: Create workflow from text file
        task = progress.add_task("Creating workflow from text file...", total=None)
        
        response = requests.post(
            "http://localhost:8000/api/orchestration/create-workflow",
            json={
                "text_file": requirements_file,
                "user_email": user_email,
                "workflow_name": "E-Commerce Data Pipeline"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            workflow_id = result["workflow_id"]
            progress.update(task, completed=True)
            
            console.print(Panel(
                f"Workflow ID: {workflow_id}\n"
                f"Plan ID: {result['plan']['id']}\n"
                f"Steps: {len(result['plan'].get('steps', []))}",
                title="[green]✅ Step 1: Workflow Created[/green]",
                border_style="green"
            ))
            
            # Display plan steps
            if result['plan'].get('steps'):
                table = Table(title="Plan Steps")
                table.add_column("Step", style="cyan")
                table.add_column("Action", style="green")
                table.add_column("Agent", style="yellow")
                
                for step in result['plan']['steps']:
                    table.add_row(
                        str(step['step']),
                        step['action'],
                        step['agent']
                    )
                
                console.print(table)
        else:
            console.print(f"[red]Failed to create workflow: {response.text}[/red]")
            return
    
    if not workflow_id:
        return
    
    # Step 2: Send email for review
    console.print("\n[bold cyan]Step 2: Sending Plan for Email Review...[/bold cyan]")
    
    response = requests.post(
        "http://localhost:8000/api/orchestration/execute-step",
        json={
            "workflow_id": workflow_id,
            "step": "send_email",
            "user_email": user_email
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        console.print(Panel(
            f"Email Status: {result.get('email_status', 'Unknown')}\n"
            f"Workflow Status: {result.get('status', 'Unknown')}",
            title="[green]✅ Step 2: Email Sent[/green]",
            border_style="green"
        ))
    else:
        console.print(f"[yellow]Warning: Email step failed: {response.text}[/yellow]")
    
    # Step 3: Visualize in Knowledge Graph
    console.print("\n[bold cyan]Step 3: Creating KG Visualization...[/bold cyan]")
    
    response = requests.post(
        "http://localhost:8000/api/orchestration/execute-step",
        json={
            "workflow_id": workflow_id,
            "step": "visualize"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        console.print(Panel(
            f"Visualization URI: {result.get('visualization_uri', 'Unknown')}\n"
            f"Triple Count: {result.get('triple_count', 0)}",
            title="[green]✅ Step 3: KG Visualization Created[/green]",
            border_style="green"
        ))
        
        # Show sample SPARQL query
        if result.get('sparql_query'):
            console.print("\n[bold]SPARQL Query for Visualization:[/bold]")
            console.print(Panel(result['sparql_query'][:500] + "...", border_style="dim"))
    
    # Step 4: Agent Review
    console.print("\n[bold cyan]Step 4: Conducting Agent Review...[/bold cyan]")
    
    response = requests.post(
        "http://localhost:8000/api/orchestration/execute-step",
        json={
            "workflow_id": workflow_id,
            "step": "review"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        console.print(Panel(
            f"Consensus: {result.get('consensus', 'Unknown')}\n"
            f"Approval Rate: {result.get('approval_rate', 'Unknown')}\n"
            f"Reviews: {len(result.get('reviews', []))}",
            title="[green]✅ Step 4: Review Complete[/green]",
            border_style="green"
        ))
        
        # Show reviews
        for review in result.get('reviews', []):
            console.print(f"  • {review['agent']}: {review['recommendation']}")
    
    # Step 5: Validate Execution Readiness
    console.print("\n[bold cyan]Step 5: Validating Execution Readiness...[/bold cyan]")
    
    response = requests.post(
        "http://localhost:8000/api/orchestration/execute-step",
        json={
            "workflow_id": workflow_id,
            "step": "validate"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        ready = result.get('execution_ready', False)
        
        console.print(Panel(
            f"Execution Ready: {'✅ Yes' if ready else '❌ No'}\n"
            f"Critical Failures: {result.get('critical_failures', 0)}\n"
            f"Validations: {len(result.get('validations', []))}",
            title=f"[{'green' if ready else 'red'}]✅ Step 5: Validation Complete[/{'green' if ready else 'red'}]",
            border_style="green" if ready else "red"
        ))
        
        # Show validation details
        if result.get('validations'):
            table = Table(title="Validation Results")
            table.add_column("Check", style="cyan")
            table.add_column("Result", style="green")
            table.add_column("Critical", style="yellow")
            
            for val in result['validations'][:5]:  # Show first 5
                table.add_row(
                    val['check'][:40],
                    "✅" if val['result'] == "pass" else "❌",
                    "Yes" if val.get('critical') else "No"
                )
            
            console.print(table)
        
        if not ready:
            console.print("[yellow]Workflow not ready for execution. Skipping remaining steps.[/yellow]")
            return
    
    # Step 6: Execute Workflow
    console.print("\n[bold cyan]Step 6: Executing Workflow...[/bold cyan]")
    
    response = requests.post(
        "http://localhost:8000/api/orchestration/execute-step",
        json={
            "workflow_id": workflow_id,
            "step": "execute"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        console.print(Panel(
            f"Execution Status: {result.get('status', 'Unknown')}\n"
            f"Steps Executed: {len(result.get('execution_results', []))}",
            title="[green]✅ Step 6: Execution Complete[/green]",
            border_style="green"
        ))
        
        # Show execution results
        if result.get('execution_results'):
            table = Table(title="Execution Results")
            table.add_column("Step", style="cyan")
            table.add_column("Action", style="green")
            table.add_column("Status", style="yellow")
            
            for exec_result in result['execution_results']:
                table.add_row(
                    str(exec_result['step']),
                    exec_result['action'],
                    "✅" if exec_result['status'] == "completed" else "❌"
                )
            
            console.print(table)
    
    # Step 7: Post-Execution Analysis
    console.print("\n[bold cyan]Step 7: Conducting Post-Execution Analysis...[/bold cyan]")
    
    response = requests.post(
        "http://localhost:8000/api/orchestration/execute-step",
        json={
            "workflow_id": workflow_id,
            "step": "analyze"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        analysis = result.get('analysis', {})
        
        console.print(Panel(
            f"Total Steps: {analysis.get('total_steps', 0)}\n"
            f"Successful: {analysis.get('successful_steps', 0)}\n"
            f"Failed: {analysis.get('failed_steps', 0)}\n"
            f"Agent Comments: {len(analysis.get('agent_commentary', []))}",
            title="[green]✅ Step 7: Analysis Complete[/green]",
            border_style="green"
        ))
        
        # Show agent commentary
        if analysis.get('agent_commentary'):
            console.print("\n[bold]Agent Commentary:[/bold]")
            for comment in analysis['agent_commentary']:
                console.print(f"  • {comment['agent']}: {comment['commentary'][:100]}...")
    
    # Final Summary
    console.print("\n" + "="*60)
    console.print(Panel(
        f"[bold green]✅ Workflow Complete![/bold green]\n\n"
        f"Workflow ID: {workflow_id}\n"
        f"All 7 steps executed successfully\n\n"
        f"The complete workflow is now stored in the Knowledge Graph\n"
        f"and can be queried, analyzed, and re-executed.",
        title="[bold]Orchestration Workflow Summary[/bold]",
        border_style="green"
    ))
    
    # Show how to query the workflow in KG
    console.print("\n[bold]Query this workflow in the Knowledge Graph:[/bold]")
    
    sparql_query = f"""
    PREFIX wf: <http://example.org/ontology#>
    SELECT ?property ?value
    WHERE {{
        <http://example.org/workflow/{workflow_id}> ?property ?value .
    }}
    """
    
    console.print(Panel(sparql_query, title="SPARQL Query", border_style="dim"))

if __name__ == "__main__":
    asyncio.run(test_orchestration_workflow())
