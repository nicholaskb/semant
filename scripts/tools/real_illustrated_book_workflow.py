#!/usr/bin/env python3
"""
Real Illustrated Book Workflow using existing Midjourney Integration
This uses the actual MidjourneyClient, GCS storage, and Knowledge Graph
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import uuid

# Import existing Midjourney integration
from midjourney_integration.client import (
    MidjourneyClient, 
    poll_until_complete,
    upload_to_gcs_and_get_public_url,
    verify_image_is_public
)
from kg.models.graph_manager import KnowledgeGraphManager

console = Console()

class RealIllustratedBookCreator:
    """Create real illustrated book using actual Midjourney API and GCS."""
    
    def __init__(self):
        self.book_title = "Quacky McWaddles' Big Adventure"
        self.workflow_id = f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.job_dir = Path("midjourney_integration/jobs")
        self.job_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize real clients
        self.mj_client = MidjourneyClient()
        self.kg_manager = None
        self.jobs_metadata = []
        
        # Selected pages to illustrate (to manage costs)
        self.pages_to_illustrate = [1]  # Testing with just one page first
        
    async def initialize(self):
        """Initialize Knowledge Graph manager."""
        self.kg_manager = KnowledgeGraphManager()
        await self.kg_manager.initialize()
        console.print("[green]✓ Knowledge Graph initialized[/green]")
        
    async def generate_illustration(self, page_num: int, prompt: str) -> Dict[str, Any]:
        """Generate a real Midjourney illustration for a page."""
        
        console.print(f"\n[cyan]Generating illustration for Page {page_num}...[/cyan]")
        
        try:
            # Submit the imagine task
            response = await self.mj_client.submit_imagine(
                prompt=prompt,
                aspect_ratio="16:9",
                model_version="V_6",
                process_mode="fast"
            )
            
            task_id = response.get("task_id")
            console.print(f"  Task ID: {task_id}")
            
            # Poll until complete
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Waiting for generation...", total=None)
                
                result = await poll_until_complete(task_id, timeout=180)
                
                progress.update(task, completed=True)
            
            # Extract the image URL from result
            output_data = result.get("output", {})
            image_url = output_data.get("image_url") or output_data.get("url")
            
            if not image_url:
                console.print(f"[red]No image URL in response for page {page_num}[/red]")
                return None
            
            console.print(f"[green]✓ Generated: {image_url}[/green]")
            
            # Save to job directory
            job_id = str(uuid.uuid4())
            job_path = self.job_dir / job_id
            job_path.mkdir(exist_ok=True)
            
            # Save metadata
            metadata = {
                "job_id": job_id,
                "task_id": task_id,
                "page_num": page_num,
                "prompt": prompt,
                "image_url": image_url,
                "workflow_id": self.workflow_id,
                "timestamp": datetime.now().isoformat(),
                "result": output_data
            }
            
            with open(job_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Upload to GCS if we have the image
            gcs_url = None
            if image_url and image_url.startswith("http"):
                try:
                    # Download the image
                    import httpx
                    async with httpx.AsyncClient() as client:
                        img_response = await client.get(image_url)
                        if img_response.status_code == 200:
                            # Save locally first
                            img_path = job_path / f"page_{page_num}.png"
                            img_path.write_bytes(img_response.content)
                            
                            # Upload to GCS
                            blob_name = f"book_illustrations/{self.workflow_id}/page_{page_num}.png"
                            gcs_url = upload_to_gcs_and_get_public_url(
                                img_response.content,
                                blob_name,
                                content_type="image/png"
                            )
                            
                            # Verify it's public
                            await verify_image_is_public(gcs_url, timeout=30)
                            
                            metadata["gcs_url"] = gcs_url
                            console.print(f"[green]✓ Uploaded to GCS: {gcs_url}[/green]")
                            
                            # Update metadata with GCS URL
                            with open(job_path / "metadata.json", "w") as f:
                                json.dump(metadata, f, indent=2)
                            
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not upload to GCS: {e}[/yellow]")
            
            # Store in Knowledge Graph
            await self.store_in_kg(metadata)
            
            self.jobs_metadata.append(metadata)
            return metadata
            
        except Exception as e:
            console.print(f"[red]Error generating illustration for page {page_num}: {e}[/red]")
            return None
    
    async def store_in_kg(self, metadata: Dict[str, Any]):
        """Store illustration metadata in the Knowledge Graph."""
        if not self.kg_manager:
            return
        
        try:
            # Create RDF triples for the illustration
            subject = f"http://example.org/book/{self.workflow_id}/page_{metadata['page_num']}"
            
            # Basic metadata
            await self.kg_manager.add_triple(
                subject=subject,
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://schema.org/ImageObject"
            )
            
            await self.kg_manager.add_triple(
                subject=subject,
                predicate="http://purl.org/dc/terms/title",
                object=f"Page {metadata['page_num']} Illustration"
            )
            
            await self.kg_manager.add_triple(
                subject=subject,
                predicate="http://schema.org/description",
                object=metadata["prompt"]
            )
            
            # Image URLs
            if metadata.get("image_url"):
                await self.kg_manager.add_triple(
                    subject=subject,
                    predicate="http://schema.org/url",
                    object=metadata["image_url"]
                )
            
            if metadata.get("gcs_url"):
                await self.kg_manager.add_triple(
                    subject=subject,
                    predicate="http://schema.org/contentUrl",
                    object=metadata["gcs_url"]
                )
            
            # Job metadata
            await self.kg_manager.add_triple(
                subject=subject,
                predicate="http://example.org/midjourney/jobId",
                object=metadata["job_id"]
            )
            
            await self.kg_manager.add_triple(
                subject=subject,
                predicate="http://example.org/midjourney/taskId",
                object=metadata["task_id"]
            )
            
            await self.kg_manager.add_triple(
                subject=subject,
                predicate="http://purl.org/dc/terms/created",
                object=metadata["timestamp"]
            )
            
            # Link to workflow
            await self.kg_manager.add_triple(
                subject=subject,
                predicate="http://purl.org/dc/terms/isPartOf",
                object=f"http://example.org/book/{self.workflow_id}"
            )
            
            console.print(f"[dim]  Stored in KG: {subject}[/dim]")
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not store in KG: {e}[/yellow]")
    
    async def run_workflow(self):
        """Run the complete real workflow."""
        
        console.print(Panel.fit(
            f"[bold cyan]🎨 Real Illustrated Book Creation[/bold cyan]\n"
            f"[yellow]{self.book_title}[/yellow]\n"
            f"Using actual Midjourney API & GCS",
            border_style="cyan"
        ))
        
        # Initialize Knowledge Graph
        await self.initialize()
        
        # Define prompts for selected pages (testing with just page 1)
        prompts = {
            1: (
                "Children's book watercolor illustration of a cute yellow duckling with "
                "comically oversized orange webbed feet, standing by a sparkly blue pond, "
                "one feather sticking up on head, bright cheerful colors, soft edges, "
                "whimsical storybook style, Maurice Sendak inspired --ar 16:9 --v 6 --stylize 750 --quality 1"
            )
        }
        
        # Generate illustrations
        console.print(f"\n[bold]Generating {len(prompts)} Key Illustrations[/bold]")
        console.print("[dim]Note: Limited to 3 pages to manage API costs[/dim]\n")
        
        for page_num, prompt in prompts.items():
            result = await self.generate_illustration(page_num, prompt)
            if result:
                console.print(f"[green]✓ Page {page_num} complete[/green]")
            await asyncio.sleep(2)  # Rate limiting
        
        # Display summary
        await self.display_summary()
        
        # Show SPARQL query example
        await self.show_sparql_queries()
    
    async def display_summary(self):
        """Display workflow summary."""
        
        console.print("\n" + "="*70)
        console.print(Panel(
            f"[bold green]✨ REAL ILLUSTRATIONS COMPLETE ✨[/bold green]\n\n"
            f"Workflow ID: {self.workflow_id}\n"
            f"Images Generated: {len(self.jobs_metadata)}",
            border_style="green"
        ))
        
        # Show generated images
        if self.jobs_metadata:
            table = Table(title="Generated Illustrations")
            table.add_column("Page", style="cyan")
            table.add_column("Job ID", style="yellow")
            table.add_column("GCS URL", style="green")
            
            for job in self.jobs_metadata:
                table.add_row(
                    str(job["page_num"]),
                    job["job_id"][:8] + "...",
                    job.get("gcs_url", "N/A")[:50] + "..."
                )
            
            console.print(table)
    
    async def show_sparql_queries(self):
        """Show example SPARQL queries for retrieving the images."""
        
        console.print("\n[bold]📊 SPARQL Queries to Retrieve Images:[/bold]\n")
        
        # Query 1: Get all illustrations for this workflow
        query1 = f"""
PREFIX schema: <http://schema.org/>
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX mj: <http://example.org/midjourney/>

SELECT ?page ?prompt ?gcs_url ?created
WHERE {{
    ?page dc:isPartOf <http://example.org/book/{self.workflow_id}> .
    ?page schema:description ?prompt .
    OPTIONAL {{ ?page schema:contentUrl ?gcs_url }}
    ?page dc:created ?created .
}}
ORDER BY ?page
"""
        
        console.print(Panel(
            query1,
            title="Query: Get all book illustrations",
            border_style="blue"
        ))
        
        # Query 2: Get specific page
        query2 = f"""
PREFIX schema: <http://schema.org/>
PREFIX mj: <http://example.org/midjourney/>

SELECT ?url ?gcs_url ?jobId
WHERE {{
    <http://example.org/book/{self.workflow_id}/page_1> schema:url ?url .
    OPTIONAL {{ 
        <http://example.org/book/{self.workflow_id}/page_1> schema:contentUrl ?gcs_url 
    }}
    <http://example.org/book/{self.workflow_id}/page_1> mj:jobId ?jobId .
}}
"""
        
        console.print(Panel(
            query2,
            title="Query: Get specific page illustration",
            border_style="blue"
        ))
        
        # Execute a sample query
        if self.kg_manager:
            console.print("\n[cyan]Executing sample query...[/cyan]")
            try:
                results = await self.kg_manager.query_graph(query1)
                if results:
                    console.print(f"[green]Found {len(results)} results in Knowledge Graph[/green]")
                    for result in results:
                        console.print(f"  • {result}")
            except Exception as e:
                console.print(f"[yellow]Query execution: {e}[/yellow]")


async def main():
    """Run the real illustrated book workflow."""
    creator = RealIllustratedBookCreator()
    
    # Check for API key
    if not os.getenv("MIDJOURNEY_API_TOKEN"):
        console.print("[red]Error: MIDJOURNEY_API_TOKEN not found in environment[/red]")
        console.print("Please set it in your .env file")
        return
    
    if not os.getenv("GCS_BUCKET_NAME"):
        console.print("[yellow]Warning: GCS_BUCKET_NAME not set, GCS upload will be skipped[/yellow]")
    
    try:
        await creator.run_workflow()
    except Exception as e:
        console.print(f"[red]Workflow error: {e}[/red]")
    finally:
        if creator.kg_manager:
            await creator.kg_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
