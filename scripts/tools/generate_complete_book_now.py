#!/usr/bin/env python3
"""
Generate the Complete Illustrated Quacky McWaddles Book
Using existing Midjourney tools and Knowledge Graph integration
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import uuid
import httpx
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import existing tools
from midjourney_integration.client import (
    MidjourneyClient, 
    poll_until_complete,
    upload_to_gcs_and_get_public_url,
    verify_image_is_public
)
from kg.models.graph_manager import KnowledgeGraphManager

console = Console()

class CompleteBookGenerator:
    """Generate the complete illustrated book using existing tools."""
    
    def __init__(self):
        self.book_title = "Quacky McWaddles' Big Adventure"
        self.workflow_id = f"complete_book_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = Path(f"complete_book_output/{self.workflow_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Job storage directory
        self.job_dir = Path("midjourney_integration/jobs")
        self.job_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize clients
        self.mj_client = MidjourneyClient()
        self.kg_manager = None
        
        # Track all generated content
        self.generated_images = {}
        self.book_content = self._get_book_content()
        
    def _get_book_content(self) -> Dict[int, Dict[str, str]]:
        """Get the complete book content."""
        return {
            1: {
                "title": "Meet Quacky McWaddles",
                "text": "*SPLASH! SPLASH! BELLY-FLOP!*\n\nDown by the sparkly pond lived a little yellow duckling named Quacky McWaddles.\n\nQuacky had the BIGGEST orange feet you ever did see!\n*Waddle-waddle-SPLAT!*",
                "prompt": "Children's book watercolor illustration, adorable yellow duckling with comically oversized orange webbed feet, standing by a sparkly blue pond, one feather sticking up on head, soft watercolor style, bright cheerful colors, whimsical, professional children's book art --ar 16:9 --v 6 --stylize 750"
            },
            2: {
                "title": "The Super Splash",
                "text": "\"Watch me do my SUPER SPLASH!\" shouted Quacky.\n\nHe ran fast as he could...\n*THUMP-THUMP-THUMP* went his big feet!\n\n*KER-SPLASH!*\n\n\"Oopsie! That was more of a belly-flop!\" giggled Quacky.",
                "prompt": "Children's book watercolor, yellow duckling mid-belly-flop into pond, huge water splash, motion lines, comic expression, big orange feet in the air, dynamic action scene, bright colors --ar 16:9 --v 6 --stylize 750"
            },
            3: {
                "title": "The Big Feet Problem",
                "text": "One morning, Quacky looked at his feet.\nThen he looked at the other ducklings' feet.\nThen he looked at his feet again.\n\n\"Holy mackerel!\" gasped Quacky. \"My feet are ENORMOUS!\"",
                "prompt": "Children's book watercolor, yellow duckling looking down at his huge orange feet, other small ducklings nearby for comparison, worried expression, pond background --ar 16:9 --v 6 --stylize 750"
            },
            4: {
                "title": "The Giggling Ducks",
                "text": "The other ducklings waddled by perfectly.\n*waddle-waddle-waddle*\n\nBut when Quacky tried...\n*Waddle-waddle-TRIP-SPLAT!*\n\n\"*Giggle-giggle!*\" laughed the other ducks.",
                "prompt": "Children's book watercolor, yellow duckling fallen over with tangled big orange feet, other ducklings laughing, embarrassed expression, playful scene --ar 16:9 --v 6 --stylize 750"
            },
            5: {
                "title": "The Journey Begins",
                "text": "Through the meadow went Quacky McWaddles.\n*SPLAT! SPLAT! SPLAT!*\nHis big feet made the funniest sounds!\n\n\"What's that noise?\" asked Freddy Frog, hopping over.",
                "prompt": "Children's book watercolor, yellow duckling walking through flowery meadow, green frog hopping nearby, big footprints in grass, sunny day --ar 16:9 --v 6 --stylize 750"
            },
            6: {
                "title": "Meeting Freddy Frog",
                "text": "\"Are you wearing FLIPPERS?\" croaked Freddy.\n\n\"Nope!\" said Quacky. \"These are my regular feet!\"\n\nFreddy laughed so hard he fell off his lily pad!\n*SPLASH!*",
                "prompt": "Children's book watercolor, yellow duckling talking to green frog on lily pad, frog looking amazed at huge orange feet, pond with lily pads --ar 16:9 --v 6 --stylize 750"
            },
            7: {
                "title": "The Tangled Mess",
                "text": "\"Oh no!\" quacked Quacky.\nHis big feet got tangled in the reedy grass!\n\nHe pulled and tugged...\n*TUG-TUG-TUG!*",
                "prompt": "Children's book watercolor, yellow duckling with huge orange feet tangled in green reeds and grass, struggling but determined expression, pond in background --ar 16:9 --v 6 --stylize 750"
            },
            8: {
                "title": "The Waddle Hop",
                "text": "Quacky had an idea!\nIf he couldn't walk... he'd HOP!\n\n*BOING! BOING! BOING!*\n\n\"I'm doing the WADDLE HOP!\"",
                "prompt": "Children's book watercolor, yellow duckling hopping with motion lines, three bunnies watching and copying, joyful expression, invented dance move --ar 16:9 --v 6 --stylize 750"
            },
            9: {
                "title": "The Wise Old Goose",
                "text": "At the top of the hill sat the Wise Old Goose.\nShe wore tiny spectacles on her beak.\n\n\"Honk-hello, young Quacky!\" she smiled.",
                "prompt": "Children's book watercolor, wise white goose with tiny spectacles on beak, sitting on hilltop, yellow duckling approaching, warm sunset colors --ar 16:9 --v 6 --stylize 750"
            },
            10: {
                "title": "The Superpower Secret",
                "text": "\"Those magnificent feet will make you the FASTEST swimmer in all the pond!\"\n\n\"Really?\" gasped Quacky.\n\n\"Your differences are your SUPERPOWERS!\"",
                "prompt": "Children's book watercolor, wise goose pointing at excited yellow duckling, pond vista below, inspirational moment, golden light --ar 16:9 --v 6 --stylize 750"
            },
            11: {
                "title": "The Swimming Race",
                "text": "Quacky WADDLE-HOPPED all the way back!\n\n\"Who wants to RACE?\" he called.\n\nInto the pond they dove!\nQuacky's big feet went *ZOOM-ZOOM-ZOOM!*",
                "prompt": "Children's book watercolor, yellow duckling swimming fast with big orange feet as propellers, water trails, other ducks racing behind, action scene --ar 16:9 --v 6 --stylize 750"
            },
            12: {
                "title": "The Happy Ending",
                "text": "\"Teach us the Waddle Hop!\" they begged.\n\nSo Quacky taught them all his silly dance.\n\nAnd from that day on, Quacky knew:\nBeing different was QUACK-A-DOODLE-AWESOME!",
                "prompt": "Children's book watercolor, all ducklings doing the Waddle Hop dance together, yellow duckling leading, celebration scene, confetti-like water drops, joyful party atmosphere --ar 16:9 --v 6 --stylize 750"
            }
        }
    
    async def initialize(self):
        """Initialize the Knowledge Graph."""
        self.kg_manager = KnowledgeGraphManager()
        await self.kg_manager.initialize()
        console.print("[green]✓ Knowledge Graph initialized[/green]")
    
    async def generate_illustration(self, page_num: int, content: Dict[str, str]) -> Dict[str, Any]:
        """Generate a real Midjourney illustration for a page."""
        
        console.print(f"\n[cyan]Page {page_num}: {content['title']}[/cyan]")
        
        try:
            # Submit the imagine task
            console.print(f"  [dim]Submitting to Midjourney...[/dim]")
            response = await self.mj_client.submit_imagine(
                prompt=content['prompt'],
                aspect_ratio="16:9",
                model_version="V_6",
                process_mode="relax"  # Use relax mode for better availability
            )
            
            # Handle the nested response structure
            if isinstance(response, dict) and "data" in response:
                task_id = response["data"].get("task_id")
            else:
                task_id = response.get("task_id")
            
            console.print(f"  Task ID: {task_id}")
            
            # Poll for completion
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("  Generating illustration...", total=None)
                result = await poll_until_complete(self.mj_client, task_id, max_wait=180)
                progress.update(task, completed=True)
            
            # Extract image URL (handle nested response structure)
            if isinstance(result, dict) and "data" in result:
                output_data = result["data"].get("output", {})
            else:
                output_data = result.get("output", {})
            
            # Try various possible URL fields
            image_url = (output_data.get("image_url") or 
                        output_data.get("url") or
                        output_data.get("discord_image_url"))
            
            if not image_url:
                console.print(f"[red]  No image URL for page {page_num}[/red]")
                return None
            
            console.print(f"[green]  ✓ Generated: {image_url[:50]}...[/green]")
            
            # Save job metadata
            job_id = str(uuid.uuid4())
            job_path = self.job_dir / job_id
            job_path.mkdir(exist_ok=True)
            
            metadata = {
                "job_id": job_id,
                "task_id": task_id,
                "page_num": page_num,
                "title": content['title'],
                "prompt": content['prompt'],
                "image_url": image_url,
                "workflow_id": self.workflow_id,
                "timestamp": datetime.now().isoformat(),
                "result": output_data
            }
            
            # Save metadata
            with open(job_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Upload to GCS
            gcs_url = await self._upload_to_gcs(image_url, page_num, job_path)
            if gcs_url:
                metadata["gcs_url"] = gcs_url
                console.print(f"[green]  ✓ Uploaded to GCS[/green]")
            
            # Store in Knowledge Graph
            await self._store_in_kg(page_num, metadata, content)
            console.print(f"[green]  ✓ Stored in Knowledge Graph[/green]")
            
            self.generated_images[page_num] = metadata
            return metadata
            
        except Exception as e:
            console.print(f"[red]Error on page {page_num}: {e}[/red]")
            return None
    
    async def _upload_to_gcs(self, image_url: str, page_num: int, job_path: Path) -> str:
        """Upload image to GCS."""
        try:
            async with httpx.AsyncClient() as client:
                img_response = await client.get(image_url)
                if img_response.status_code == 200:
                    # Save locally
                    img_path = job_path / f"page_{page_num}.png"
                    img_path.write_bytes(img_response.content)
                    
                    # Upload to GCS
                    blob_name = f"book_illustrations/{self.workflow_id}/page_{page_num}.png"
                    gcs_url = upload_to_gcs_and_get_public_url(
                        img_response.content,
                        blob_name,
                        content_type="image/png"
                    )
                    
                    # Verify public access
                    await verify_image_is_public(gcs_url, timeout=30)
                    return gcs_url
        except Exception as e:
            console.print(f"[yellow]  Warning: GCS upload failed: {e}[/yellow]")
            return None
    
    async def _store_in_kg(self, page_num: int, metadata: Dict, content: Dict):
        """Store illustration metadata in Knowledge Graph."""
        if not self.kg_manager:
            return
        
        subject = f"http://example.org/book/{self.workflow_id}/page_{page_num}"
        
        # Type
        await self.kg_manager.add_triple(
            subject=subject,
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            object="http://schema.org/ImageObject"
        )
        
        # Title
        await self.kg_manager.add_triple(
            subject=subject,
            predicate="http://purl.org/dc/terms/title",
            object=f"Page {page_num}: {content['title']}"
        )
        
        # Prompt
        await self.kg_manager.add_triple(
            subject=subject,
            predicate="http://schema.org/description",
            object=content['prompt']
        )
        
        # URLs
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
        
        # Metadata
        await self.kg_manager.add_triple(
            subject=subject,
            predicate="http://example.org/midjourney/jobId",
            object=metadata["job_id"]
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
    
    async def generate_book_files(self):
        """Generate the final book files."""
        
        # Generate Markdown
        md_path = self.output_dir / "quacky_mcwaddles_complete.md"
        md_content = f"# {self.book_title}\n\n"
        md_content += "*A Complete 12-Page Illustrated Adventure*\n\n---\n\n"
        
        for page_num, content in self.book_content.items():
            md_content += f"## Page {page_num}: {content['title']}\n\n"
            
            if page_num in self.generated_images:
                img = self.generated_images[page_num]
                img_url = img.get("gcs_url") or img.get("image_url", "")
                md_content += f"![Illustration]({img_url})\n\n"
            
            md_content += f"{content['text']}\n\n---\n\n"
        
        md_path.write_text(md_content)
        console.print(f"[green]✓ Created: {md_path}[/green]")
        
        # Generate metadata JSON
        meta_path = self.output_dir / "book_metadata.json"
        metadata = {
            "title": self.book_title,
            "workflow_id": self.workflow_id,
            "created_at": datetime.now().isoformat(),
            "pages_generated": len(self.generated_images),
            "total_pages": 12,
            "illustrations": self.generated_images
        }
        
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        console.print(f"[green]✓ Created: {meta_path}[/green]")
    
    async def run(self):
        """Run the complete book generation."""
        
        console.print(Panel.fit(
            f"[bold cyan]📚 GENERATING COMPLETE ILLUSTRATED BOOK[/bold cyan]\n"
            f"[yellow]{self.book_title}[/yellow]\n"
            f"12 Pages with Real Midjourney Illustrations",
            border_style="cyan"
        ))
        
        # Initialize
        await self.initialize()
        
        # Generate illustrations (limiting to save costs)
        pages_to_generate = [1, 3, 5, 7, 9, 11]  # Key story moments
        
        console.print(f"\n[bold]Generating {len(pages_to_generate)} Key Illustrations[/bold]")
        console.print("[dim]Note: Limited pages to manage API costs[/dim]\n")
        
        for page_num in pages_to_generate:
            content = self.book_content[page_num]
            await self.generate_illustration(page_num, content)
            await asyncio.sleep(3)  # Rate limiting
        
        # Generate output files
        console.print("\n[bold]Creating Book Files[/bold]")
        await self.generate_book_files()
        
        # Summary
        console.print("\n" + "="*70)
        console.print(Panel(
            f"[bold green]✨ BOOK GENERATION COMPLETE! ✨[/bold green]\n\n"
            f"Workflow ID: {self.workflow_id}\n"
            f"Pages Generated: {len(self.generated_images)}/12\n"
            f"Output Directory: {self.output_dir}",
            border_style="green"
        ))
        
        # SPARQL query example
        if self.generated_images:
            console.print("\n[bold]Query your book with SPARQL:[/bold]")
            console.print(f"""
SELECT ?page ?title ?gcs_url
WHERE {{
    ?page dc:isPartOf <http://example.org/book/{self.workflow_id}> .
    ?page dc:title ?title .
    OPTIONAL {{ ?page schema:contentUrl ?gcs_url }}
}}""")
        
        if self.kg_manager:
            await self.kg_manager.shutdown()


async def main():
    """Generate the complete book."""
    
    # Load .env file
    load_dotenv()
    
    # Check environment
    if not os.getenv("MIDJOURNEY_API_TOKEN"):
        console.print("[red]Error: MIDJOURNEY_API_TOKEN not set[/red]")
        console.print("Please check your .env file contains MIDJOURNEY_API_TOKEN")
        return
    
    generator = CompleteBookGenerator()
    
    try:
        await generator.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Generation interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        if generator.kg_manager:
            await generator.kg_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
