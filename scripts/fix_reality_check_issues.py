#!/usr/bin/env python3
"""
Diagnostic and fix script for reality check issues.
Checks current state and provides actionable recommendations.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from qdrant_client import QdrantClient
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import httpx

console = Console()

def check_qdrant() -> Dict[str, Any]:
    """Check Qdrant status."""
    try:
        client = QdrantClient(host="localhost", port=6333)
        collections = client.get_collections()
        collection_exists = any(c.name == "childrens_book_images" for c in collections.collections)
        
        if collection_exists:
            collection_info = client.get_collection("childrens_book_images")
            points_count = collection_info.points_count
        else:
            points_count = 0
        
        return {
            "connected": True,
            "collection_exists": collection_exists,
            "points_count": points_count,
            "status": "✅ Connected" if points_count > 0 else "⚠️ Empty"
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "status": "❌ Not connected"
        }

def check_knowledge_graph() -> Dict[str, Any]:
    """Check Knowledge Graph file status."""
    kg_file = Path("knowledge_graph_persistent.n3")
    backup_file = Path("knowledge_graph_persistent.n3.backup")
    corrupted_file = Path("knowledge_graph_persistent.n3.corrupted")
    
    result = {
        "file_exists": kg_file.exists(),
        "file_size": kg_file.stat().st_size if kg_file.exists() else 0,
        "backup_exists": backup_file.exists(),
        "backup_size": backup_file.stat().st_size if backup_file.exists() else 0,
        "corrupted_exists": corrupted_file.exists(),
    }
    
    # Try to load and count triples
    if kg_file.exists() and kg_file.stat().st_size > 0:
        try:
            from kg.models.graph_manager import KnowledgeGraphManager
            kg = KnowledgeGraphManager(persistent_storage=True)
            # Don't initialize here - just check file
            result["triples_estimate"] = "Unknown (need to load)"
        except Exception as e:
            result["load_error"] = str(e)
    
    return result

def check_local_images() -> Dict[str, Any]:
    """Count local images ready for ingestion."""
    base_dir = Path("generated_books")
    if not base_dir.exists():
        return {
            "exists": False,
            "input_count": 0,
            "output_count": 0,
            "total": 0
        }
    
    input_images = list(base_dir.rglob("input/*.png")) + list(base_dir.rglob("input/*.jpg")) + list(base_dir.rglob("input/*.jpeg"))
    output_images = list(base_dir.rglob("output/*.png")) + list(base_dir.rglob("output/*.jpg")) + list(base_dir.rglob("output/*.jpeg"))
    
    return {
        "exists": True,
        "input_count": len(input_images),
        "output_count": len(output_images),
        "total": len(input_images) + len(output_images)
    }

async def check_api_server() -> Dict[str, Any]:
    """Check if API server is running."""
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{api_url}/api/health")
                if response.status_code == 200:
                    return {
                        "running": True,
                        "status": "✅ Running",
                        "url": api_url
                    }
            except Exception:
                # Try root endpoint
                response = await client.get(f"{api_url}/")
                if response.status_code in [200, 404]:
                    return {
                        "running": True,
                        "status": "✅ Running (no /health endpoint)",
                        "url": api_url
                    }
            return {
                "running": False,
                "status": "❌ Not responding",
                "url": api_url
            }
    except Exception as e:
        return {
            "running": False,
            "status": "❌ Not running",
            "error": str(e),
            "url": api_url
        }

def print_status_table(qdrant: Dict, kg: Dict, images: Dict, api: Dict):
    """Print a comprehensive status table."""
    table = Table(title="System Status Check", show_header=True, header_style="bold cyan")
    table.add_column("Component", style="cyan", width=25)
    table.add_column("Status", style="green", width=30)
    table.add_column("Details", style="yellow", width=40)
    
    # Qdrant
    qdrant_status = qdrant.get("status", "Unknown")
    qdrant_details = f"Points: {qdrant.get('points_count', 0)}" if qdrant.get("connected") else qdrant.get("error", "N/A")
    table.add_row("Qdrant", qdrant_status, qdrant_details)
    
    # Knowledge Graph
    kg_status = "✅ File exists" if kg.get("file_exists") else "❌ No file"
    kg_size = kg.get("file_size", 0)
    kg_details = f"Size: {kg_size} bytes"
    if kg.get("backup_exists"):
        kg_details += f" | Backup: {kg.get('backup_size', 0)} bytes"
    table.add_row("Knowledge Graph", kg_status, kg_details)
    
    # Local Images
    images_status = f"✅ {images.get('total', 0)} images" if images.get("exists") else "❌ No images"
    images_details = f"Input: {images.get('input_count', 0)}, Output: {images.get('output_count', 0)}"
    table.add_row("Local Images", images_status, images_details)
    
    # API Server
    api_status = api.get("status", "Unknown")
    api_details = api.get("url", "N/A")
    table.add_row("API Server", api_status, api_details)
    
    console.print(table)

def print_recommendations(qdrant: Dict, kg: Dict, images: Dict, api: Dict):
    """Print actionable recommendations."""
    console.print("\n" + "="*70)
    console.print("[bold cyan]Recommendations[/bold cyan]")
    console.print("="*70)
    
    recommendations = []
    
    # Qdrant
    if not qdrant.get("connected"):
        recommendations.append({
            "priority": "🔴 HIGH",
            "action": "Start Qdrant",
            "command": "docker run -d -p 6333:6333 qdrant/qdrant:latest"
        })
    elif qdrant.get("points_count", 0) == 0:
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "action": "Ingest images (Qdrant is empty)",
            "command": "python scripts/ingest_local_images_to_qdrant.py"
        })
    
    # API Server
    if not api.get("running"):
        recommendations.append({
            "priority": "🔴 HIGH",
            "action": "Start API Server",
            "command": "python main.py"
        })
    
    # Knowledge Graph
    if kg.get("file_size", 0) == 0 and kg.get("backup_exists"):
        recommendations.append({
            "priority": "🟢 LOW",
            "action": "Restore KG from backup (optional)",
            "command": "cp knowledge_graph_persistent.n3.backup knowledge_graph_persistent.n3"
        })
    
    # Images
    if images.get("total", 0) > 0 and not api.get("running"):
        recommendations.append({
            "priority": "🟡 MEDIUM",
            "action": f"Ingest {images.get('total')} images (after API starts)",
            "command": "python scripts/ingest_local_images_to_qdrant.py"
        })
    
    if not recommendations:
        console.print("[bold green]✅ All systems operational![/bold green]")
        return
    
    rec_table = Table(show_header=True, header_style="bold cyan")
    rec_table.add_column("Priority", style="red", width=10)
    rec_table.add_column("Action", style="cyan", width=30)
    rec_table.add_column("Command", style="green", width=50)
    
    for rec in recommendations:
        rec_table.add_row(rec["priority"], rec["action"], rec["command"])
    
    console.print(rec_table)
    
    # Next steps
    console.print("\n[bold cyan]Next Steps:[/bold cyan]")
    step_num = 1
    if not api.get("running"):
        console.print(f"{step_num}. Start API server: [green]python main.py[/green]")
        step_num += 1
    if qdrant.get("connected") and qdrant.get("points_count", 0) == 0 and images.get("total", 0) > 0:
        console.print(f"{step_num}. Ingest images: [green]python scripts/ingest_local_images_to_qdrant.py[/green]")
        step_num += 1
    if step_num == 1:
        console.print("✅ All systems ready!")

async def main():
    console.print(Panel.fit(
        "[bold cyan]Reality Check Diagnostic Tool[/bold cyan]\n"
        "Checking system status and providing recommendations",
        border_style="cyan"
    ))
    
    console.print("\n[cyan]Checking components...[/cyan]")
    
    # Check all components
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task1 = progress.add_task("Checking Qdrant...", total=None)
        qdrant = check_qdrant()
        progress.update(task1, completed=True)
        
        task2 = progress.add_task("Checking Knowledge Graph...", total=None)
        kg = check_knowledge_graph()
        progress.update(task2, completed=True)
        
        task3 = progress.add_task("Checking local images...", total=None)
        images = check_local_images()
        progress.update(task3, completed=True)
        
        task4 = progress.add_task("Checking API server...", total=None)
        api = await check_api_server()
        progress.update(task4, completed=True)
    
    # Print status
    print_status_table(qdrant, kg, images, api)
    
    # Print recommendations
    print_recommendations(qdrant, kg, images, api)
    
    # Summary
    console.print("\n" + "="*70)
    if qdrant.get("connected") and api.get("running") and qdrant.get("points_count", 0) > 0:
        console.print("[bold green]✅ System is ready![/bold green]")
    else:
        console.print("[bold yellow]⚠️  System needs attention - see recommendations above[/bold yellow]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
