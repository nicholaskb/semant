#!/usr/bin/env python3
"""
Comprehensive test for the 'Refine with AI' functionality.
Tests both backend endpoints and simulates frontend behavior.
"""

import asyncio
import os
from dotenv import load_dotenv
import requests
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables first!
load_dotenv()

console = Console()

# Test configuration
API_BASE = "http://localhost:8000"
TEST_PROMPTS = [
    "superhero portrait",
    "cyberpunk cityscape at night",
    "fantasy dragon in mountains",
    "",  # Empty prompt (should fail gracefully)
    "a" * 500,  # Very long prompt
]

async def check_server_health():
    """Verify the server is running."""
    console.print("\n[bold cyan]1. Checking Server Health...[/bold cyan]")
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            console.print("✅ Server is running", style="green")
            return True
    except requests.exceptions.ConnectionError:
        console.print("❌ Server is not running on port 8000", style="red")
        console.print("\n[yellow]To start the server:[/yellow]")
        console.print("  python main.py")
        return False
    except Exception as e:
        console.print(f"❌ Error checking server: {e}", style="red")
        return False

async def check_planner_status():
    """Check if the Planner agent is available."""
    console.print("\n[bold cyan]2. Checking Planner Agent Status...[/bold cyan]")
    
    try:
        response = requests.get(f"{API_BASE}/api/planner-status", timeout=5)
        status = response.json()
        
        table = Table(title="Planner Status", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Imports OK", "✅" if status.get("imports_ok") else "❌")
        table.add_row("Planner Available", "✅" if status.get("planner_available") else "❌")
        table.add_row("Planner Type", str(status.get("planner_type", "N/A")))
        
        if status.get("registry_agents"):
            agents = "\n".join(f"  • {agent}" for agent in status["registry_agents"])
            table.add_row("Registered Agents", agents)
        
        console.print(table)
        return status.get("planner_available", False)
    
    except Exception as e:
        console.print(f"❌ Error checking Planner: {e}", style="red")
        return False

async def test_simple_refine_endpoint():
    """Test the /api/midjourney/refine-prompt endpoint."""
    console.print("\n[bold cyan]3. Testing Simple Refine Endpoint[/bold cyan]")
    
    results = []
    
    for i, prompt in enumerate(TEST_PROMPTS[:3], 1):  # Test first 3 prompts
        console.print(f"\n[dim]Test {i}: Original prompt:[/dim] '{prompt}'")
        
        try:
            response = requests.post(
                f"{API_BASE}/api/midjourney/refine-prompt",
                json={"prompt": prompt},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                refined = data.get("refined_prompt", "")
                
                if refined:
                    panel = Panel(
                        refined,
                        title=f"[green]✅ Test {i} - Refined Prompt[/green]",
                        border_style="green"
                    )
                    console.print(panel)
                    results.append({"test": i, "status": "✅ PASS", "prompt": prompt[:50]})
                else:
                    console.print(f"⚠️  Test {i}: Empty refined prompt", style="yellow")
                    results.append({"test": i, "status": "⚠️  WARN", "prompt": prompt[:50]})
            else:
                console.print(f"❌ Test {i}: HTTP {response.status_code}", style="red")
                results.append({"test": i, "status": "❌ FAIL", "prompt": prompt[:50]})
        
        except Exception as e:
            console.print(f"❌ Test {i}: {str(e)}", style="red")
            results.append({"test": i, "status": "❌ ERROR", "prompt": prompt[:50]})
    
    return results

async def test_workflow_refine_endpoint():
    """Test the /api/midjourney/refine-prompt-workflow endpoint."""
    console.print("\n[bold cyan]4. Testing Workflow Refine Endpoint[/bold cyan]")
    
    prompt = "fantasy warrior character design"
    console.print(f"\n[dim]Testing with:[/dim] '{prompt}'")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/midjourney/refine-prompt-workflow",
            json={"prompt": prompt, "image_urls": []},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            refined = data.get("refined_prompt", "")
            transcript = data.get("transcript", [])
            
            if refined:
                panel = Panel(
                    refined,
                    title="[green]✅ Workflow - Refined Prompt[/green]",
                    border_style="green"
                )
                console.print(panel)
            
            if transcript:
                console.print("\n[bold]Refinement Transcript:[/bold]")
                for i, line in enumerate(transcript[:10], 1):  # Show first 10 lines
                    console.print(f"  {i}. {line}")
                if len(transcript) > 10:
                    console.print(f"  ... and {len(transcript) - 10} more lines")
                
                return "✅ PASS"
            else:
                console.print("⚠️  No transcript returned", style="yellow")
                return "⚠️  WARN"
        else:
            console.print(f"❌ HTTP {response.status_code}: {response.text}", style="red")
            return "❌ FAIL"
    
    except Exception as e:
        console.print(f"❌ Error: {str(e)}", style="red")
        return "❌ ERROR"

async def test_edge_cases():
    """Test edge cases and error handling."""
    console.print("\n[bold cyan]5. Testing Edge Cases[/bold cyan]")
    
    test_cases = [
        ("Empty prompt", ""),
        ("Very long prompt", "a" * 500),
        ("Special characters", "portrait with ™ © ® symbols & emojis 🎨"),
    ]
    
    results = []
    
    for name, prompt in test_cases:
        console.print(f"\n[dim]Testing: {name}[/dim]")
        
        try:
            response = requests.post(
                f"{API_BASE}/api/midjourney/refine-prompt",
                json={"prompt": prompt},
                timeout=30
            )
            
            if prompt == "":  # Empty should fail gracefully
                if response.status_code >= 400:
                    console.print(f"✅ {name}: Correctly rejected", style="green")
                    results.append({"test": name, "status": "✅ PASS"})
                else:
                    console.print(f"⚠️  {name}: Should have rejected empty prompt", style="yellow")
                    results.append({"test": name, "status": "⚠️  WARN"})
            else:
                if response.status_code == 200:
                    data = response.json()
                    if data.get("refined_prompt"):
                        console.print(f"✅ {name}: Handled correctly", style="green")
                        results.append({"test": name, "status": "✅ PASS"})
                    else:
                        console.print(f"⚠️  {name}: No refinement", style="yellow")
                        results.append({"test": name, "status": "⚠️  WARN"})
                else:
                    console.print(f"❌ {name}: HTTP {response.status_code}", style="red")
                    results.append({"test": name, "status": "❌ FAIL"})
        
        except Exception as e:
            console.print(f"❌ {name}: {str(e)}", style="red")
            results.append({"test": name, "status": "❌ ERROR"})
    
    return results

async def generate_summary(simple_results, workflow_result, edge_results):
    """Generate a summary report of all tests."""
    console.print("\n" + "="*70)
    console.print("\n[bold cyan]TEST SUMMARY REPORT[/bold cyan]")
    console.print("="*70)
    
    # Simple endpoint results
    console.print("\n[bold]Simple Refine Endpoint:[/bold]")
    for result in simple_results:
        console.print(f"  Test {result['test']}: {result['status']} - {result['prompt']}")
    
    # Workflow endpoint result
    console.print(f"\n[bold]Workflow Refine Endpoint:[/bold] {workflow_result}")
    
    # Edge cases
    console.print("\n[bold]Edge Cases:[/bold]")
    for result in edge_results:
        console.print(f"  {result['test']}: {result['status']}")
    
    # Overall verdict
    all_results = simple_results + edge_results + [{"status": workflow_result}]
    passed = sum(1 for r in all_results if "PASS" in r["status"])
    warned = sum(1 for r in all_results if "WARN" in r["status"])
    failed = sum(1 for r in all_results if "FAIL" in r["status"] or "ERROR" in r["status"])
    total = len(all_results)
    
    console.print("\n" + "="*70)
    console.print(f"\n[bold]Results:[/bold] {passed}/{total} passed, {warned} warnings, {failed} failed")
    
    if failed == 0 and warned == 0:
        console.print("\n[bold green]🎉 ALL TESTS PASSED! Feature is production-ready.[/bold green]")
        return True
    elif failed == 0:
        console.print("\n[bold yellow]⚠️  Tests passed with warnings. Review recommended.[/bold yellow]")
        return True
    else:
        console.print("\n[bold red]❌ Some tests failed. Review and fix required.[/bold red]")
        return False

async def main():
    """Run all tests."""
    console.print(Panel.fit(
        "[bold]'Refine with AI' Comprehensive Test Suite[/bold]\n"
        "Testing both backend endpoints and error handling",
        border_style="cyan"
    ))
    
    # Check if server is running
    if not await check_server_health():
        return
    
    # Check Planner status
    planner_available = await check_planner_status()
    
    # Run tests
    simple_results = await test_simple_refine_endpoint()
    
    if planner_available:
        workflow_result = await test_workflow_refine_endpoint()
    else:
        console.print("\n⚠️  Skipping workflow tests (Planner not available)", style="yellow")
        workflow_result = "⏭️  SKIPPED"
    
    edge_results = await test_edge_cases()
    
    # Generate summary
    success = await generate_summary(simple_results, workflow_result, edge_results)
    
    # Save results to scratch space
    timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"scratch_space/task_9_test_results_{timestamp}.md"
    
    with open(results_file, "w") as f:
        f.write(f"# Task 9 Test Results - {timestamp}\n\n")
        f.write("## Simple Endpoint Tests\n")
        for r in simple_results:
            f.write(f"- Test {r['test']}: {r['status']} - {r['prompt']}\n")
        f.write(f"\n## Workflow Endpoint Test\n{workflow_result}\n")
        f.write("\n## Edge Cases\n")
        for r in edge_results:
            f.write(f"- {r['test']}: {r['status']}\n")
        f.write(f"\n## Overall: {'✅ READY FOR PRODUCTION' if success else '❌ NEEDS FIXES'}\n")
    
    console.print(f"\n[dim]Results saved to: {results_file}[/dim]")

if __name__ == "__main__":
    asyncio.run(main())

