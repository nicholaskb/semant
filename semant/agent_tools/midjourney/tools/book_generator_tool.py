"""
Agent tool for generating complete illustrated books using Midjourney.
This tool allows agents to create full illustrated children's books.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from semant.agent_tools.midjourney.goapi_client import GoAPIClient
from semant.agent_tools.midjourney.kg_logging import KGLogger
from midjourney_integration.client import (
    MidjourneyClient,
    poll_until_complete,
    upload_to_gcs_and_get_public_url
)
from kg.models.graph_manager import KnowledgeGraphManager


class BookGeneratorTool:
    """
    Agent tool for generating complete illustrated books.
    This tool orchestrates the entire book creation process including:
    - Story content management
    - Illustration generation via Midjourney
    - GCS storage
    - Knowledge Graph logging
    """
    
    def __init__(
        self, 
        client: Optional[MidjourneyClient] = None,
        kg_logger: Optional[KGLogger] = None,
        kg_manager: Optional[KnowledgeGraphManager] = None,
        agent_id: str = "agent/BookGenerator"
    ):
        """Initialize the book generator tool."""
        self.client = client or MidjourneyClient()
        self.kg_logger = kg_logger or KGLogger(agent_id=agent_id)
        self.kg_manager = kg_manager
        self.agent_id = agent_id
        self.workflow_id = None
        self.job_dir = Path("midjourney_integration/jobs")
        self.job_dir.mkdir(parents=True, exist_ok=True)
        
    async def initialize_kg(self):
        """Initialize Knowledge Graph if not already done."""
        if not self.kg_manager:
            self.kg_manager = KnowledgeGraphManager()
            await self.kg_manager.initialize()
    
    async def generate_book(
        self,
        title: str,
        pages: List[Dict[str, str]],
        workflow_id: Optional[str] = None,
        output_dir: Optional[str] = None,
        max_pages_to_illustrate: int = 6
    ) -> Dict[str, Any]:
        """
        Generate a complete illustrated book.
        
        Args:
            title: Book title
            pages: List of page dicts with 'title', 'text', and 'prompt' keys
            workflow_id: Optional workflow ID (auto-generated if not provided)
            output_dir: Optional output directory path
            max_pages_to_illustrate: Maximum number of pages to illustrate (cost control)
            
        Returns:
            Dict containing workflow_id, generated_images, and output_paths
        """
        
        # Initialize workflow
        self.workflow_id = workflow_id or f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_path = Path(output_dir or f"agent_books/{self.workflow_id}")
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize KG if needed
        await self.initialize_kg()
        
        # Log workflow start
        await self.kg_logger.log_tool_call(
            tool_name="book_generator.start",
            inputs={
                "title": title,
                "workflow_id": self.workflow_id,
                "total_pages": len(pages),
                "pages_to_illustrate": min(len(pages), max_pages_to_illustrate)
            },
            outputs={"status": "started"}
        )
        
        # Generate illustrations for selected pages
        generated_images = {}
        pages_to_illustrate = pages[:max_pages_to_illustrate]
        
        for idx, page in enumerate(pages_to_illustrate):
            page_num = idx + 1
            image_data = await self._generate_illustration(page_num, page)
            if image_data:
                generated_images[page_num] = image_data
            
            # Rate limiting
            await asyncio.sleep(2)
        
        # Generate output files
        output_files = await self._create_output_files(
            title, pages, generated_images, output_path
        )
        
        # Log workflow completion
        result = {
            "workflow_id": self.workflow_id,
            "title": title,
            "pages_generated": len(generated_images),
            "total_pages": len(pages),
            "output_files": output_files,
            "generated_images": generated_images
        }
        
        await self.kg_logger.log_tool_call(
            tool_name="book_generator.complete",
            inputs={"workflow_id": self.workflow_id},
            outputs=result
        )
        
        return result
    
    async def _generate_illustration(
        self, 
        page_num: int, 
        page_data: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Generate a single illustration for a page."""
        
        try:
            print(f"Generating illustration for page {page_num}: {page_data.get('title', '')}")
            
            # Submit to Midjourney
            response = await self.client.submit_imagine(
                prompt=page_data.get("prompt", ""),
                aspect_ratio="16:9",
                model_version="V_6",
                process_mode="relax"
            )
            
            print(f"Imagine response for page {page_num}: {response}")
            
            # Extract task_id from response
            if isinstance(response, dict) and "data" in response:
                task_id = response["data"].get("task_id")
            else:
                task_id = response.get("task_id")
            
            if not task_id:
                print(f"No task_id for page {page_num}")
                return None
            
            print(f"Task ID for page {page_num}: {task_id}")
            
            # Poll for completion
            result = await poll_until_complete(self.client, task_id, max_wait=180)
            
            # Extract image URL
            if isinstance(result, dict) and "data" in result:
                output_data = result["data"].get("output", {})
            else:
                output_data = result.get("output", {})
            
            image_url = (output_data.get("image_url") or 
                        output_data.get("url") or
                        output_data.get("discord_image_url"))
            
            if not image_url:
                return None
            
            # Save metadata
            job_id = str(uuid.uuid4())
            job_path = self.job_dir / job_id
            job_path.mkdir(exist_ok=True)
            
            metadata = {
                "job_id": job_id,
                "task_id": task_id,
                "page_num": page_num,
                "title": page_data.get("title", ""),
                "prompt": page_data.get("prompt", ""),
                "image_url": image_url,
                "workflow_id": self.workflow_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Save to job directory
            with open(job_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Try to upload to GCS
            gcs_url = await self._upload_to_gcs(image_url, page_num, job_path)
            if gcs_url:
                metadata["gcs_url"] = gcs_url
            
            # Store in Knowledge Graph
            await self._store_in_kg(page_num, metadata, page_data)
            
            # Log the generation
            await self.kg_logger.log_tool_call(
                tool_name="book_generator.generate_illustration",
                inputs={
                    "page_num": page_num,
                    "prompt": page_data.get("prompt", "")
                },
                outputs=metadata,
                goapi_task={"task_id": task_id},
                images=[image_url]
            )
            
            return metadata
            
        except Exception as e:
            # Log error
            await self.kg_logger.log_tool_call(
                tool_name="book_generator.illustration_error",
                inputs={"page_num": page_num},
                outputs={"error": str(e)}
            )
            return None
    
    async def _upload_to_gcs(
        self, 
        image_url: str, 
        page_num: int, 
        job_path: Path
    ) -> Optional[str]:
        """Upload image to Google Cloud Storage."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                if response.status_code == 200:
                    # Save locally
                    img_path = job_path / f"page_{page_num}.png"
                    img_path.write_bytes(response.content)
                    
                    # Upload to GCS
                    blob_name = f"book_illustrations/{self.workflow_id}/page_{page_num}.png"
                    gcs_url = upload_to_gcs_and_get_public_url(
                        response.content,
                        blob_name,
                        content_type="image/png"
                    )
                    return gcs_url
        except Exception as e:
            print(f"GCS upload failed: {e}")
            return None
    
    async def _store_in_kg(
        self, 
        page_num: int, 
        metadata: Dict, 
        page_data: Dict
    ):
        """Store illustration metadata in Knowledge Graph."""
        if not self.kg_manager:
            return
        
        subject = f"http://example.org/book/{self.workflow_id}/page_{page_num}"
        
        # Add triples
        await self.kg_manager.add_triple(
            subject=subject,
            predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            object="http://schema.org/ImageObject"
        )
        
        await self.kg_manager.add_triple(
            subject=subject,
            predicate="http://purl.org/dc/terms/title",
            object=f"Page {page_num}: {page_data.get('title', '')}"
        )
        
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
        
        await self.kg_manager.add_triple(
            subject=subject,
            predicate="http://purl.org/dc/terms/isPartOf",
            object=f"http://example.org/book/{self.workflow_id}"
        )
    
    async def _create_output_files(
        self,
        title: str,
        pages: List[Dict],
        generated_images: Dict,
        output_path: Path
    ) -> Dict[str, str]:
        """Create output files for the book."""
        
        # Generate Markdown
        md_path = output_path / "book.md"
        md_content = f"# {title}\n\n"
        
        for idx, page in enumerate(pages):
            page_num = idx + 1
            md_content += f"## Page {page_num}: {page.get('title', '')}\n\n"
            
            if page_num in generated_images:
                img = generated_images[page_num]
                img_url = img.get("gcs_url") or img.get("image_url", "")
                md_content += f"![Illustration]({img_url})\n\n"
            
            md_content += f"{page.get('text', '')}\n\n---\n\n"
        
        md_path.write_text(md_content)
        
        # Generate metadata JSON
        meta_path = output_path / "metadata.json"
        metadata = {
            "title": title,
            "workflow_id": self.workflow_id,
            "created_at": datetime.now().isoformat(),
            "pages_generated": len(generated_images),
            "total_pages": len(pages),
            "agent_id": self.agent_id,
            "illustrations": generated_images
        }
        
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return {
            "markdown": str(md_path),
            "metadata": str(meta_path)
        }
    
    async def run(
        self,
        *,
        title: str,
        pages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Main entry point for the agent tool.
        
        This method is called by agents to generate a book.
        """
        return await self.generate_book(title, pages, **kwargs)
