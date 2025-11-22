#!/usr/bin/env python3
"""
Trend-Driven Book Generator.

This script:
1. Connects to Knowledge Graph to find the top trending topic.
2. Generates a children's book story based on that trend.
3. Orchestrates the book creation process using:
   - ChildrensBookOrchestrator (with project_id linked to trend)
   - Existing image assets (clustered by style)
   - Dynamic story generation

Schema:
    trend:Trend -> triggers -> project:BookProject
"""

import asyncio
import os
import sys
import uuid
from typing import List, Dict, Any
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from rich.console import Console
from rdflib import Namespace

# Import internal modules
try:
    from kg.models.graph_manager import KnowledgeGraphManager
    from semant.workflows.childrens_book.orchestrator import ChildrensBookOrchestrator, STORY_SCRIPT
except ImportError:
    # If running from scripts directory, adjust imports
    sys.path.insert(0, str(project_root.parent))
    from kg.models.graph_manager import KnowledgeGraphManager
    from semant.workflows.childrens_book.orchestrator import ChildrensBookOrchestrator, STORY_SCRIPT

# Load environment variables
load_dotenv()
console = Console()

# Namespaces
TREND = Namespace("http://example.org/trend#")
KG = Namespace("http://example.org/kg#")

class TrendBookCreator:
    def __init__(self):
        self.kg_manager = KnowledgeGraphManager(persistent_storage=True)

    async def get_top_trend(self, country: str = "US") -> Dict[str, Any]:
        """Get the top trending topic from KG."""
        await self.kg_manager.initialize()
        
        # SPARQL query to get top trend by rank/score
        query = f"""
        PREFIX trend: <http://example.org/trend#>
        
        SELECT ?trend ?name ?score WHERE {{
            ?trend a trend:Trend ;
                   trend:country "{country}" ;
                   trend:name ?name .
            OPTIONAL {{ ?trend trend:score ?score . }}
        }}
        ORDER BY DESC(?score)
        LIMIT 1
        """
        
        results = await self.kg_manager.query_graph(query)
        
        if not results:
            # Fallback if no trends found in KG
            console.print(f"[yellow]⚠️ No trends found for {country} in KG. Using fallback trend.[/yellow]")
            return {
                "uri": "http://example.org/trend/fallback",
                "name": "Artificial Intelligence",
                "score": 100
            }
            
        trend = results[0]
        return {
            "uri": trend["trend"],
            "name": trend["name"],
            "score": trend.get("score", 0)
        }

    def generate_story_from_trend(self, trend_name: str) -> List[Dict[str, Any]]:
        """
        Generate a story script based on the trend.
        In a real system, this would use an LLM.
        For now, we use a template.
        """
        console.print(f"[cyan]🤖 Generating story for trend: {trend_name}[/cyan]")
        
        # Use the same structure as STORY_SCRIPT but adapt the content
        # We'll generate a 6-page story for this demo
        story = [
            {
                "page": 1,
                "lines": [f"Once upon a time, in a world where everyone talked about {trend_name}, something magical happened."]
            },
            {
                "page": 2,
                "lines": [f"{trend_name} was more than just a word; it was a spark that lit up the sky."]
            },
            {
                "page": 3,
                "lines": ["But one little curious explorer decided to see what was behind the noise."]
            },
            {
                "page": 4,
                "lines": [f"Deep inside the heart of {trend_name}, they found a secret door to imagination."]
            },
            {
                "page": 5,
                "lines": ["Through the door was a land of pure wonder, where ideas grew like tall trees."]
            },
            {
                "page": 6,
                "lines": [f"And that is how {trend_name} changed the world forever, one dream at a time."]
            }
        ]
        return story

    async def create_book(self):
        """Main workflow."""
        console.print("[bold green]🚀 Starting Trend-Driven Book Generation[/bold green]")
        
        # 1. Get Top Trend
        trend = await self.get_top_trend()
        trend_name = trend["name"]
        console.print(f"[green]📈 Top Trend: {trend_name}[/green]")
        
        # 2. Generate Story
        story_script = self.generate_story_from_trend(trend_name)
        
        # 3. Prepare Project ID
        # We use a project_id derived from the trend to link them
        # Sanitize trend name for project ID
        import re
        safe_trend_name = re.sub(r'[^a-zA-Z0-9]', '_', trend_name).lower()
        project_id = f"trend_book_{safe_trend_name}_{uuid.uuid4().hex[:4]}"
        console.print(f"[blue]🆔 Project ID: {project_id}[/blue]")
        
        # 4. Run Orchestrator
        # We pass the custom story script and the project_id
        # The Orchestrator will use these to tag images and generate the book
        try:
            orchestrator = ChildrensBookOrchestrator(
                project_id=project_id,
                story_script=story_script,
                # Using default bucket settings from .env
                # bucket_name=os.getenv("GCS_BUCKET_NAME")
            )
            
            await orchestrator.initialize()
            
            console.print("[yellow]⚡ Generating book...[/yellow]")
            
            # This will use existing images (clustered/paired) if available,
            # or fallback to placeholders/generation.
            # Since we are using a new project_id, it might not find exact matches 
            # unless we implement "semantic pairing" in the future.
            # For now, it proves the flow from Trend -> Project -> Book.
            result = await orchestrator.generate_book()
            
            if result.get("book", {}).get("html_path"):
                console.print(f"[bold green]✅ Book generated successfully![/bold green]")
                console.print(f"   HTML: {result['book']['html_path']}")
                
                # Try to open the book
                try:
                    import webbrowser
                    webbrowser.open(f"file://{os.path.abspath(result['book']['html_path'])}")
                except:
                    pass
            else:
                console.print("[red]❌ Book generation failed to produce HTML.[/red]")
                
        except Exception as e:
            console.print(f"[red]❌ Execution failed: {e}[/red]")
            import traceback
            traceback.print_exc()
        finally:
            await self.kg_manager.shutdown()

if __name__ == "__main__":
    creator = TrendBookCreator()
    asyncio.run(creator.create_book())
