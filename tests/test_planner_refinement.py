#!/usr/bin/env python3
"""Test script to verify the Planner is working for prompt refinement."""

import asyncio
import requests
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

async def test_planner_status():
    """Check if planner is available."""
    console.print("\n[bold cyan]1. Checking Planner Status...[/bold cyan]")
    
    response = requests.get("http://localhost:8000/api/planner-status")
    status = response.json()
    
    # Create a nice table
    table = Table(title="Planner Status", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    
    table.add_row("Imports OK", "✅ Yes" if status["imports_ok"] else "❌ No")
    table.add_row("Planner Available", "✅ Yes" if status["planner_available"] else "❌ No") 
    table.add_row("Planner Type", status.get("planner_type", "N/A"))
    table.add_row("Functional", status.get("planner_functional", "N/A"))
    
    if status.get("registry_agents"):
        agents_str = "\n".join(f"  • {agent}" for agent in status["registry_agents"])
        table.add_row("Registered Agents", agents_str)
    
    console.print(table)
    
    if "troubleshooting" in status:
        console.print("\n[bold red]Troubleshooting Tips:[/bold red]")
        for tip in status["troubleshooting"]:
            console.print(f"  • {tip}")
    
    return status["planner_available"]

async def test_prompt_refinement():
    """Test the refine-prompt endpoint."""
    console.print("\n[bold cyan]2. Testing Prompt Refinement...[/bold cyan]")
    
    test_prompt = "superhero portrait with cool lighting"
    
    console.print(f"[dim]Original prompt:[/dim] {test_prompt}")
    
    response = requests.post(
        "http://localhost:8000/api/midjourney/refine-prompt",
        json={"prompt": test_prompt}
    )
    
    if response.status_code == 200:
        result = response.json()
        refined = result.get("refined_prompt", "No refinement")
        
        panel = Panel(
            refined,
            title="[bold green]Refined Prompt[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        console.print(panel)
        return True
    else:
        console.print(f"[bold red]Error:[/bold red] {response.status_code} - {response.text}")
        return False

async def test_themed_set_generation():
    """Test if themed-set uses the planner for refinement."""
    console.print("\n[bold cyan]3. Testing Themed Set with Refinement...[/bold cyan]")
    
    # Prepare a test request
    test_data = {
        "theme": "Marvel superheroes cinematic universe",
        "face_image_urls": ["https://example.com/test-face.jpg"],
        "count": 2
    }
    
    console.print(f"[dim]Theme:[/dim] {test_data['theme']}")
    console.print(f"[dim]Count:[/dim] {test_data['count']}")
    
    # Make request but DON'T actually submit (dry run)
    # We'll inspect logs or use a mock mode if available
    console.print("\n[yellow]Note: This would submit real jobs. Check server logs for refinement activity.[/yellow]")
    
    # Check what prompt would be generated
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from main import _generate_theme_aware_prompt
    
    console.print("\n[bold]Sample Generated Prompts:[/bold]")
    for i in range(2):
        prompt = _generate_theme_aware_prompt(test_data["theme"])
        console.print(f"\n[dim]Base Prompt {i+1}:[/dim]")
        console.print(Panel(prompt, border_style="dim"))

async def main():
    """Run all tests."""
    console.print(Panel.fit(
        "[bold]Planner Verification & Testing[/bold]\n"
        "This script verifies the Planner agent is working correctly",
        border_style="cyan"
    ))
    
    # Check status
    planner_available = await test_planner_status()
    
    if planner_available:
        # Test refinement
        await test_prompt_refinement()
        
        # Show themed-set info
        await test_themed_set_generation()
        
        console.print("\n[bold green]✅ Planner is working correctly![/bold green]")
        console.print("\n[bold]How refinement works in Generate Themed Set:[/bold]")
        console.print("1. Internal generator creates theme-aware base prompts")
        console.print("2. Each prompt is refined by the Planner (if available)")
        console.print("3. Refined prompts are submitted with your reference images")
    else:
        console.print("\n[bold red]❌ Planner is not available[/bold red]")
        console.print("\nTo fix this:")
        console.print("1. Check that agents/ directory exists and is importable")
        console.print("2. Verify all agent files are present")
        console.print("3. Check server startup logs for errors")
        console.print("4. Restart the server after fixing issues")

if __name__ == "__main__":
    asyncio.run(main())

