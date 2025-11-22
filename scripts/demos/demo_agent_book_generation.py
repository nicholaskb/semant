#!/usr/bin/env python3
"""
Demonstrate how agents can use the BookGeneratorTool to create illustrated books.
"""

import asyncio
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Import the agent tools
from semant.agent_tools.midjourney import REGISTRY

console = Console()

# Define the Quacky McWaddles book content
QUACKY_BOOK = {
    "title": "Quacky McWaddles' Big Adventure",
    "pages": [
        {
            "title": "Meet Quacky McWaddles",
            "text": "*SPLASH! SPLASH! BELLY-FLOP!*\n\nDown by the sparkly pond lived a little yellow duckling named Quacky McWaddles.\n\nQuacky had the BIGGEST orange feet you ever did see!",
            "prompt": "Children's book watercolor illustration, adorable yellow duckling with comically oversized orange webbed feet, standing by a sparkly blue pond, one feather sticking up on head, soft watercolor style, bright cheerful colors --ar 16:9 --v 6"
        },
        {
            "title": "The Super Splash",
            "text": "\"Watch me do my SUPER SPLASH!\" shouted Quacky.\n\n*KER-SPLASH!*\n\n\"Oopsie! That was more of a belly-flop!\"",
            "prompt": "Children's book watercolor, yellow duckling mid-belly-flop into pond, huge water splash, motion lines, comic expression, big orange feet in the air --ar 16:9 --v 6"
        },
        {
            "title": "The Big Feet Problem",
            "text": "One morning, Quacky looked at his feet.\n\n\"Holy mackerel!\" gasped Quacky. \"My feet are ENORMOUS!\"",
            "prompt": "Children's book watercolor, yellow duckling looking down at his huge orange feet, worried expression, other small ducklings nearby for comparison --ar 16:9 --v 6"
        },
        {
            "title": "The Tangled Mess",
            "text": "\"Oh no!\" quacked Quacky.\nHis big feet got tangled in the reedy grass!\n\n*TUG-TUG-TUG!*",
            "prompt": "Children's book watercolor, yellow duckling with huge orange feet tangled in green reeds and grass, struggling but determined expression --ar 16:9 --v 6"
        },
        {
            "title": "The Waddle Hop",
            "text": "Quacky had an idea!\nIf he couldn't walk... he'd HOP!\n\n*BOING! BOING! BOING!*\n\n\"I'm doing the WADDLE HOP!\"",
            "prompt": "Children's book watercolor, yellow duckling hopping with motion lines, three bunnies watching and copying, joyful expression --ar 16:9 --v 6"
        },
        {
            "title": "The Happy Ending",
            "text": "\"Teach us the Waddle Hop!\" they begged.\n\nAnd from that day on, Quacky knew:\nBeing different was QUACK-A-DOODLE-AWESOME!",
            "prompt": "Children's book watercolor, all ducklings doing the Waddle Hop dance together, yellow duckling leading, celebration scene, confetti-like water drops --ar 16:9 --v 6"
        }
    ]
}

async def demonstrate_agent_book_generation():
    """Show how an agent would use the BookGeneratorTool."""
    
    # Load environment variables
    load_dotenv()
    
    console.print(Panel.fit(
        "[bold cyan]🤖 Agent Book Generation Demo[/bold cyan]\n"
        "Demonstrating the mj.book_generator agent tool",
        border_style="cyan"
    ))
    
    # Step 1: Agent discovers the tool
    console.print("\n[bold]Step 1: Agent discovers available tools[/bold]")
    console.print("[dim]Agent queries the tool registry...[/dim]")
    
    available_tools = list(REGISTRY.keys())
    console.print(f"\n[green]Found {len(available_tools)} tools:[/green]")
    for tool_name in available_tools:
        if "book" in tool_name:
            console.print(f"  [cyan]• {tool_name}[/cyan] ← Book generation tool!")
        else:
            console.print(f"  • {tool_name}")
    
    # Step 2: Agent initializes the tool
    console.print("\n[bold]Step 2: Agent initializes the BookGeneratorTool[/bold]")
    
    # Get the tool factory from registry
    book_tool_factory = REGISTRY.get("mj.book_generator")
    if not book_tool_factory:
        console.print("[red]Error: mj.book_generator not found in registry[/red]")
        return
    
    # Create the tool instance
    book_tool = book_tool_factory()
    console.print("[green]✓ BookGeneratorTool initialized[/green]")
    
    # Step 3: Agent prepares the book content
    console.print("\n[bold]Step 3: Agent prepares book content[/bold]")
    console.print(f"  Title: [yellow]{QUACKY_BOOK['title']}[/yellow]")
    console.print(f"  Pages: [yellow]{len(QUACKY_BOOK['pages'])} pages[/yellow]")
    
    # Step 4: Agent calls the tool
    console.print("\n[bold]Step 4: Agent generates the book[/bold]")
    console.print("[dim]Agent calls: await book_tool.run(...)[/dim]\n")
    
    try:
        result = await book_tool.run(
            title=QUACKY_BOOK["title"],
            pages=QUACKY_BOOK["pages"],
            max_pages_to_illustrate=3  # Limit for demo
        )
        
        # Display results
        console.print(Panel(
            f"[bold green]✨ Book Generation Complete![/bold green]\n\n"
            f"Workflow ID: {result.get('workflow_id')}\n"
            f"Pages Generated: {result.get('pages_generated')}/{result.get('total_pages')}\n"
            f"Output Files: {result.get('output_files', {})}",
            border_style="green"
        ))
        
        # Show how to query the Knowledge Graph
        console.print("\n[bold]Step 5: Agent queries Knowledge Graph for results[/bold]")
        console.print("[dim]SPARQL query to retrieve book illustrations:[/dim]\n")
        
        workflow_id = result.get('workflow_id')
        query = f"""
PREFIX schema: <http://schema.org/>
PREFIX dc: <http://purl.org/dc/terms/>

SELECT ?page ?title ?image_url ?gcs_url
WHERE {{
    ?page dc:isPartOf <http://example.org/book/{workflow_id}> .
    ?page dc:title ?title .
    OPTIONAL {{ ?page schema:url ?image_url }}
    OPTIONAL {{ ?page schema:contentUrl ?gcs_url }}
}}
ORDER BY ?page"""
        
        console.print(Markdown(f"```sparql\n{query}\n```"))
        
    except Exception as e:
        console.print(f"[red]Error generating book: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    # Step 6: Summary
    console.print("\n[bold cyan]Summary: Agent Tool Integration[/bold cyan]")
    console.print("""
The BookGeneratorTool provides agents with:
• Complete book generation capability
• Automatic Midjourney illustration
• GCS storage integration  
• Knowledge Graph logging
• SPARQL-queryable results

Agents can now create illustrated books by simply calling:
[green]book_tool.run(title=..., pages=...)[/green]
""")


async def main():
    """Main entry point."""
    await demonstrate_agent_book_generation()


if __name__ == "__main__":
    asyncio.run(main())

