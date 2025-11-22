#!/usr/bin/env python3
"""
DUCK BOOK WITH COMPLETE KNOWLEDGE GRAPH INTEGRATION
Stores all generation data in KG for full tracking
"""

import asyncio
from datetime import datetime
from pathlib import Path
import json
from dotenv import load_dotenv
from kg.models.graph_manager import KnowledgeGraphManager
from midjourney_integration.client import MidjourneyClient
from semant.agent_tools.midjourney.kg_logging import KGLogger

load_dotenv()

class DuckBookKGSystem:
    """Complete duck book system with KG integration."""
    
    def __init__(self):
        self.kg_manager = KnowledgeGraphManager()
        self.kg_logger = KGLogger()
        self.mj_client = MidjourneyClient()
        self.book_id = f"duck_book_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    async def initialize(self):
        """Initialize KG."""
        await self.kg_manager.initialize()
        await self.kg_logger.initialize()
        
        # Create book instance in KG
        book_triple = {
            "subject": f"book:{self.book_id}",
            "predicate": "rdf:type",
            "object": "schema:Book"
        }
        await self.kg_manager.add_triple(
            book_triple["subject"],
            book_triple["predicate"],
            book_triple["object"]
        )
        
        # Add book metadata
        await self.kg_manager.add_triple(
            f"book:{self.book_id}",
            "schema:name",
            "Quacky McWaddles' Big Adventure"
        )
        
        await self.kg_manager.add_triple(
            f"book:{self.book_id}",
            "schema:description",
            "A children's book about a duckling with big feet (NOT A FOX!)"
        )
        
        await self.kg_manager.add_triple(
            f"book:{self.book_id}",
            "schema:dateCreated",
            datetime.now().isoformat()
        )
        
        print(f"✅ Book registered in KG: {self.book_id}")
    
    async def store_page_in_kg(self, page_data, task_result=None):
        """Store page data and generation info in KG."""
        
        page_id = f"page:{self.book_id}_p{page_data['page']}"
        
        # Create page node
        await self.kg_manager.add_triple(
            page_id,
            "rdf:type",
            "schema:CreativeWork"
        )
        
        # Link page to book
        await self.kg_manager.add_triple(
            f"book:{self.book_id}",
            "schema:hasPart",
            page_id
        )
        
        # Store page metadata
        await self.kg_manager.add_triple(
            page_id,
            "schema:position",
            str(page_data['page'])
        )
        
        await self.kg_manager.add_triple(
            page_id,
            "schema:name",
            page_data['title']
        )
        
        await self.kg_manager.add_triple(
            page_id,
            "schema:text",
            page_data['text']
        )
        
        # Store prompt used
        prompt_id = f"prompt:{page_id}"
        await self.kg_manager.add_triple(
            prompt_id,
            "rdf:type",
            "mj:Prompt"
        )
        
        await self.kg_manager.add_triple(
            prompt_id,
            "mj:promptText",
            page_data['prompt']
        )
        
        await self.kg_manager.add_triple(
            page_id,
            "mj:usedPrompt",
            prompt_id
        )
        
        # Store task info if available
        if page_data.get('task_id'):
            task_id = f"task:{page_data['task_id']}"
            
            await self.kg_manager.add_triple(
                task_id,
                "rdf:type",
                "mj:Task"
            )
            
            await self.kg_manager.add_triple(
                task_id,
                "mj:taskId",
                page_data['task_id']
            )
            
            await self.kg_manager.add_triple(
                task_id,
                "mj:status",
                page_data.get('status', 'pending')
            )
            
            await self.kg_manager.add_triple(
                page_id,
                "mj:generatedBy",
                task_id
            )
            
            # Store result if available
            if task_result and task_result.get('image_url'):
                image_id = f"image:{page_id}"
                
                await self.kg_manager.add_triple(
                    image_id,
                    "rdf:type",
                    "schema:ImageObject"
                )
                
                await self.kg_manager.add_triple(
                    image_id,
                    "schema:contentUrl",
                    task_result['image_url']
                )
                
                if task_result.get('gcs_url'):
                    await self.kg_manager.add_triple(
                        image_id,
                        "mj:gcsUrl",
                        task_result['gcs_url']
                    )
                
                await self.kg_manager.add_triple(
                    page_id,
                    "schema:image",
                    image_id
                )
        
        print(f"  💾 Stored in KG: {page_id}")
    
    async def check_and_update_tasks(self, task_ids):
        """Check task status and update KG."""
        
        results = {}
        
        for task_id in task_ids:
            try:
                # Poll task
                result = await self.mj_client.poll_task(task_id)
                data = result.get('data', result)
                status = data.get('status')
                
                # Update task status in KG
                task_node = f"task:{task_id}"
                await self.kg_manager.add_triple(
                    task_node,
                    "mj:status",
                    status
                )
                
                await self.kg_manager.add_triple(
                    task_node,
                    "mj:lastChecked",
                    datetime.now().isoformat()
                )
                
                # If completed, store image
                if status in ['completed', 'finished']:
                    output = data.get('output', {})
                    image_url = (output.get('discord_image_url') or 
                               output.get('image_url') or
                               output.get('url'))
                    
                    if image_url:
                        # Upload to GCS
                        gcs_url = await self.mj_client.upload_to_gcs_and_get_public_url(
                            image_url,
                            f"duck_book/{task_id}.png"
                        )
                        
                        results[task_id] = {
                            'status': 'completed',
                            'image_url': image_url,
                            'gcs_url': gcs_url
                        }
                        
                        # Store in KG
                        await self.kg_manager.add_triple(
                            task_node,
                            "mj:imageUrl",
                            image_url
                        )
                        
                        if gcs_url:
                            await self.kg_manager.add_triple(
                                task_node,
                                "mj:gcsUrl",
                                gcs_url
                            )
                else:
                    results[task_id] = {'status': status}
                
                print(f"  Task {task_id[:8]}... - Status: {status}")
                
            except Exception as e:
                print(f"  ❌ Error checking {task_id}: {e}")
                results[task_id] = {'status': 'error', 'error': str(e)}
        
        return results
    
    async def generate_book_with_kg(self):
        """Generate complete book with KG tracking."""
        
        await self.initialize()
        
        print("\n🦆 GENERATING DUCK BOOK WITH KNOWLEDGE GRAPH")
        print("="*60)
        
        # Duck pages data
        pages = [
            {
                "page": 1,
                "title": "Meet Quacky",
                "text": "Down by the sparkly pond lived Quacky McWaddles with the BIGGEST orange feet!",
                "prompt": "cute yellow DUCKLING with oversized orange webbed feet by blue pond, watercolor illustration, NO FOX",
            },
            {
                "page": 2,
                "title": "The Problem",
                "text": "Oh no! My feet are too big! The other ducklings giggled.",
                "prompt": "sad yellow DUCKLING looking at huge feet, other ducklings laughing, watercolor, NO FOX",
            },
            {
                "page": 3,
                "title": "The Journey",
                "text": "I'll find the Wise Old Goose! She'll know what to do!",
                "prompt": "determined yellow DUCKLING walking through meadow, watercolor adventure, NO FOX",
            },
            {
                "page": 4,
                "title": "Meeting Friends",
                "text": "Are you wearing FLIPPERS? asked Freddy Frog.",
                "prompt": "yellow DUCKLING meeting green FROG, frog pointing at big feet, watercolor, NO FOX",
            },
            {
                "page": 5,
                "title": "The Waddle Hop",
                "text": "If I can't walk, I'll HOP! BOING BOING BOING!",
                "prompt": "yellow DUCKLING hopping with bunnies watching, motion lines, watercolor, NO FOX",
            },
            {
                "page": 6,
                "title": "Happy Ending",
                "text": "Being different is QUACK-A-DOODLE-AWESOME!",
                "prompt": "DUCKLINGS celebrating by pond, yellow duck center, party, watercolor, NO FOX",
            }
        ]
        
        # Check existing duck tasks first
        existing_task_ids = [
            "47494efb-efdb-4769-8d11-e409409c542b",  # Page 1
            "803960aa-e50d-40c5-816e-a1e60e223972",  # Page 2
            "496e186f-9f5a-4318-ac31-8c030bfd8876",  # Page 3
            "524d57d9-5c68-4e92-8a4a-1b4431416bfb",  # Page 4
            "ac3ab948-74b2-4837-93ed-ed30232977b7",  # Page 5
            "40450532-49b9-47f5-ab94-eefff9fc114b",  # Page 6
        ]
        
        # Add task IDs to pages
        for i, (page, task_id) in enumerate(zip(pages, existing_task_ids)):
            page['task_id'] = task_id
            page['status'] = 'submitted'
        
        # Store all pages in KG
        print("\n📊 STORING IN KNOWLEDGE GRAPH:")
        for page in pages:
            await self.store_page_in_kg(page)
        
        # Check task status
        print("\n🔍 CHECKING TASK STATUS:")
        results = await self.check_and_update_tasks(existing_task_ids)
        
        # Query KG for stored data
        print("\n📈 KNOWLEDGE GRAPH CONTENTS:")
        
        # Query for all pages
        query = f"""
        PREFIX schema: <http://schema.org/>
        PREFIX mj: <http://midjourney.com/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?page ?title ?prompt ?taskId ?status ?imageUrl
        WHERE {{
            <book:{self.book_id}> schema:hasPart ?page .
            ?page schema:name ?title .
            ?page mj:usedPrompt ?promptNode .
            ?promptNode mj:promptText ?prompt .
            OPTIONAL {{ 
                ?page mj:generatedBy ?task .
                ?task mj:taskId ?taskId .
                ?task mj:status ?status .
                OPTIONAL {{ ?task mj:imageUrl ?imageUrl }}
            }}
        }}
        ORDER BY ?page
        """
        
        kg_results = await self.kg_manager.query_graph(query)
        
        print("\nStored in KG:")
        for result in kg_results:
            print(f"  Page: {result.get('title')}")
            print(f"    Task: {result.get('taskId', 'N/A')[:8]}...")
            print(f"    Status: {result.get('status', 'N/A')}")
        
        # Generate report
        await self.generate_kg_report()
        
        print("\n✅ ALL DATA STORED IN KNOWLEDGE GRAPH!")
        
    async def generate_kg_report(self):
        """Generate HTML report showing KG contents."""
        
        output_dir = Path("duck_book_kg_report")
        output_dir.mkdir(exist_ok=True)
        
        # Get all data from KG
        query = f"""
        PREFIX schema: <http://schema.org/>
        PREFIX mj: <http://midjourney.com/>
        
        SELECT *
        WHERE {{
            <book:{self.book_id}> ?bookPred ?bookObj .
            OPTIONAL {{
                <book:{self.book_id}> schema:hasPart ?page .
                ?page ?pagePred ?pageObj .
            }}
        }}
        """
        
        results = await self.kg_manager.query_graph(query)
        
        # Create report
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Duck Book - Knowledge Graph Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
        .report {{ max-width: 1200px; margin: auto; background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #FF6B35; }}
        .kg-data {{ background: #E8F5E9; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .triple {{ background: white; padding: 10px; margin: 10px 0; border-left: 4px solid #4CAF50; }}
        code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="report">
        <h1>🦆 Duck Book Knowledge Graph Report</h1>
        <p>Book ID: <code>{self.book_id}</code></p>
        
        <div class="kg-data">
            <h2>📊 Stored Triples</h2>
            <p>Total triples: {len(results)}</p>
            
            {self._format_triples(results)}
        </div>
        
        <div class="kg-data">
            <h2>✅ What's Stored</h2>
            <ul>
                <li>Book metadata (title, description, creation date)</li>
                <li>All 6 pages with titles and text</li>
                <li>Prompts used for each page</li>
                <li>Midjourney task IDs</li>
                <li>Task status and results</li>
                <li>Image URLs (Discord and GCS)</li>
            </ul>
        </div>
    </div>
</body>
</html>"""
        
        report_path = output_dir / "kg_report.html"
        report_path.write_text(html)
        
        print(f"\n📊 KG Report: {report_path}")
        
        return report_path
    
    def _format_triples(self, results):
        """Format triples for display."""
        html = ""
        for r in results[:20]:  # Show first 20
            html += f"""<div class="triple">
                <code>{r.get('bookPred', r.get('pagePred', 'predicate'))}</code> → 
                <code>{r.get('bookObj', r.get('pageObj', 'object'))}</code>
            </div>"""
        if len(results) > 20:
            html += f"<p>... and {len(results) - 20} more triples</p>"
        return html


async def main():
    system = DuckBookKGSystem()
    await system.generate_book_with_kg()
    
    # Shutdown KG
    await system.kg_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

