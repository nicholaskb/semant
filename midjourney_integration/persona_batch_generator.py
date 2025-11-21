"""
Persona-Themed Batch Generation System
======================================
Allows users to upload persona photos and generate themed images with
version-aware cref/oref handling, rate-limited concurrency, and comprehensive logging.
"""

import asyncio
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from loguru import logger
from kg.models.graph_manager import KnowledgeGraphManager
from midjourney_integration.client import MidjourneyClient, upload_to_gcs_and_get_public_url, poll_until_complete
from semant.agent_tools.midjourney.workflows import generate_themed_portraits


class PersonaBatchGenerator:
    """
    Orchestrates batch generation of themed images using persona photos.
    
    Features:
    - Rate-limited concurrent processing
    - Version-aware cross-reference (cref) and outpainting reference (oref) handling
    - Knowledge Graph integration for tracking
    - Comprehensive error handling and recovery
    """
    
    def __init__(
        self, 
        knowledge_graph: KnowledgeGraphManager,
        midjourney_client: MidjourneyClient,
        max_concurrent: int = 3
    ):
        """
        Initialize the batch generator.
        
        Args:
            knowledge_graph: KG manager for tracking generation process
            midjourney_client: Client for Midjourney API interactions
            max_concurrent: Maximum concurrent operations (default 3 for rate limiting)
        """
        self.kg = knowledge_graph
        self.mj_client = midjourney_client
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.batch_id = None
        self.results = []
        self.errors = []
        
        logger.info(f"PersonaBatchGenerator initialized with max_concurrent={max_concurrent}")
    
    async def validate_inputs(
        self, 
        persona_images: List[str], 
        theme_prompt: str,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Validate inputs for batch generation.
        
        Args:
            persona_images: List of persona image URLs (must be 6)
            theme_prompt: Theme description (e.g., "Lord of the Rings")
            batch_size: Number of images to generate (default 10)
            
        Returns:
            Validation result with status and any errors
        """
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check persona images count
        if len(persona_images) != 6:
            validation["valid"] = False
            validation["errors"].append(
                f"Exactly 6 persona images required, got {len(persona_images)}"
            )
        
        # Validate URLs are accessible
        for i, url in enumerate(persona_images):
            if not url.startswith(("http://", "https://")):
                validation["valid"] = False
                validation["errors"].append(
                    f"Persona image {i+1} has invalid URL: {url}"
                )
        
        # Validate theme prompt
        if not theme_prompt or len(theme_prompt.strip()) < 3:
            validation["valid"] = False
            validation["errors"].append("Theme prompt must be at least 3 characters")
        
        # Validate batch size
        if batch_size < 1 or batch_size > 100:
            validation["valid"] = False
            validation["errors"].append("Batch size must be between 1 and 100")
        
        # Check MJ version for cref/oref compatibility
        mj_version = self.mj_client.get_version() if hasattr(self.mj_client, 'get_version') else "6"
        if mj_version == "7":
            validation["warnings"].append(
                "MJ v7 detected - will use oref instead of cref for persona references"
            )
        
        return validation
    
    async def generate_themed_batch(
        self,
        persona_images: List[str],
        theme_prompt: str,
        batch_size: int = 10,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a batch of themed images using persona references.
        
        Args:
            persona_images: List of 6 persona image URLs
            theme_prompt: Theme for generation (e.g., "Lord of the Rings")
            batch_size: Number of images to generate
            model_version: Optional MJ model version override
            
        Returns:
            Batch generation results including generated images and metadata
        """
        # Validate inputs
        validation = await self.validate_inputs(persona_images, theme_prompt, batch_size)
        if not validation["valid"]:
            logger.error(f"Validation failed: {validation['errors']}")
            return {
                "success": False,
                "errors": validation["errors"],
                "batch_id": None
            }
        
        # Generate unique batch ID
        self.batch_id = f"batch_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Starting batch generation: {self.batch_id}")
        
        # Store batch metadata in KG
        await self._store_batch_metadata(persona_images, theme_prompt, batch_size, model_version)
        
        # Determine version-specific parameters
        use_oref = model_version == "7" if model_version else False
        reference_param = "oref" if use_oref else "cref"
        
        # Generate images with rate limiting
        generation_tasks = []
        for i in range(batch_size):
            # Cycle through persona images
            persona_idx = i % len(persona_images)
            persona_url = persona_images[persona_idx]
            
            # Create generation task
            task = self._generate_single_image(
                persona_url=persona_url,
                theme_prompt=theme_prompt,
                reference_param=reference_param,
                image_index=i,
                model_version=model_version
            )
            generation_tasks.append(task)
        
        # Execute with concurrency control
        results = await asyncio.gather(*generation_tasks, return_exceptions=True)
        
        # Process results
        successful = []
        failed = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append({
                    "index": i,
                    "error": str(result)
                })
                logger.error(f"Failed to generate image {i}: {result}")
            else:
                successful.append(result)
                logger.info(f"Successfully generated image {i}")
        
        # Store final results in KG
        await self._store_batch_results(successful, failed)
        
        # Return comprehensive results
        return {
            "success": len(successful) > 0,
            "batch_id": self.batch_id,
            "theme": theme_prompt,
            "total_requested": batch_size,
            "total_generated": len(successful),
            "total_failed": len(failed),
            "generated_images": successful,
            "errors": failed,
            "metadata": {
                "model_version": model_version,
                "reference_type": reference_param,
                "persona_count": len(persona_images),
                "timestamp": datetime.now().isoformat()
            }
        }
    
    async def _generate_single_image(
        self,
        persona_url: str,
        theme_prompt: str,
        reference_param: str,
        image_index: int,
        model_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a single themed image with rate limiting.
        
        Args:
            persona_url: URL of the persona reference image
            theme_prompt: Theme description
            reference_param: "cref" or "oref" based on version
            image_index: Index of this image in the batch
            model_version: Optional model version
            
        Returns:
            Generated image data
        """
        async with self.semaphore:  # Rate limiting
            try:
                # Construct prompt with reference
                if reference_param == "oref":
                    # Version 7 syntax
                    full_prompt = f"{theme_prompt} --{reference_param} {persona_url}"
                else:
                    # Version 6 syntax  
                    full_prompt = f"{persona_url} {theme_prompt} --{reference_param} {persona_url}"
                
                if model_version:
                    full_prompt += f" --v {model_version}"
                
                # Add variation for diversity
                full_prompt += f" --seed {image_index * 137}"  # Prime number for variation
                
                logger.info(f"Generating image {image_index} with prompt: {full_prompt[:100]}...")
                
                # Submit to Midjourney
                response = await self.mj_client.submit_imagine(full_prompt)
                task_id = response.get("data", {}).get("task_id")
                
                if not task_id:
                    raise Exception(f"No task_id received for image {image_index}")
                
                # Poll for completion
                result = await poll_until_complete(
                    client=self.mj_client,
                    task_id=task_id,
                    kg_manager=self.kg
                )
                
                # Extract image URL
                image_url = result.get("output", {}).get("url")
                if not image_url:
                    raise Exception(f"No image URL in result for image {image_index}")
                
                return {
                    "index": image_index,
                    "task_id": task_id,
                    "image_url": image_url,
                    "persona_url": persona_url,
                    "prompt": full_prompt,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error generating image {image_index}: {e}")
                raise
    
    async def _store_batch_metadata(
        self,
        persona_images: List[str],
        theme_prompt: str,
        batch_size: int,
        model_version: Optional[str]
    ):
        """Store batch metadata in Knowledge Graph."""
        batch_uri = f"http://example.org/batch/{self.batch_id}"
        
        # Store batch information
        await self.kg.add_triple(
            batch_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/PersonaBatch"
        )
        
        await self.kg.add_triple(
            batch_uri,
            "http://example.org/theme",
            theme_prompt
        )
        
        await self.kg.add_triple(
            batch_uri,
            "http://example.org/batchSize",
            str(batch_size)
        )
        
        if model_version:
            await self.kg.add_triple(
                batch_uri,
                "http://example.org/modelVersion",
                model_version
            )
        
        # Store persona references
        for i, persona_url in enumerate(persona_images):
            await self.kg.add_triple(
                batch_uri,
                f"http://example.org/persona_{i}",
                persona_url
            )
        
        await self.kg.add_triple(
            batch_uri,
            "http://example.org/startTime",
            datetime.now().isoformat()
        )
        
        logger.info(f"Stored batch metadata in KG: {self.batch_id}")
    
    async def _store_batch_results(
        self,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]]
    ):
        """Store batch generation results in Knowledge Graph."""
        batch_uri = f"http://example.org/batch/{self.batch_id}"
        
        # Store completion time
        await self.kg.add_triple(
            batch_uri,
            "http://example.org/endTime",
            datetime.now().isoformat()
        )
        
        # Store success count
        await self.kg.add_triple(
            batch_uri,
            "http://example.org/successCount",
            str(len(successful))
        )
        
        # Store failure count
        await self.kg.add_triple(
            batch_uri,
            "http://example.org/failureCount",
            str(len(failed))
        )
        
        # Store successful image references
        for img in successful:
            img_uri = f"http://example.org/image/{img['task_id']}"
            
            await self.kg.add_triple(
                batch_uri,
                "http://example.org/generatedImage",
                img_uri
            )
            
            await self.kg.add_triple(
                img_uri,
                "http://example.org/imageUrl",
                img['image_url']
            )
            
            await self.kg.add_triple(
                img_uri,
                "http://example.org/imageIndex",
                str(img['index'])
            )
        
        logger.info(f"Stored batch results in KG: {len(successful)} successful, {len(failed)} failed")
    
    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Get the status of a batch generation process.
        
        Args:
            batch_id: The batch identifier
            
        Returns:
            Batch status information
        """
        batch_uri = f"http://example.org/batch/{batch_id}"
        
        # Query KG for batch information
        query = f"""
        PREFIX ex: <http://example.org/>
        
        SELECT ?property ?value WHERE {{
            <{batch_uri}> ?property ?value .
        }}
        """
        
        results = await self.kg.query_graph(query)
        
        if not results:
            return {
                "found": False,
                "batch_id": batch_id
            }
        
        # Process results into status dict
        status = {
            "found": True,
            "batch_id": batch_id,
            "properties": {}
        }
        
        for r in results:
            prop = str(r['property']).split('/')[-1]
            status["properties"][prop] = str(r['value'])
        
        return status


async def create_batch_generator(
    kg_manager: Optional[KnowledgeGraphManager] = None,
    mj_client: Optional[MidjourneyClient] = None,
    max_concurrent: int = 3
) -> PersonaBatchGenerator:
    """
    Factory function to create a PersonaBatchGenerator instance.
    
    Args:
        kg_manager: Optional KG manager (creates new if not provided)
        mj_client: Optional MJ client (creates new if not provided)
        max_concurrent: Maximum concurrent operations
        
    Returns:
        Initialized PersonaBatchGenerator
    """
    # Initialize KG if not provided
    if not kg_manager:
        kg_manager = KnowledgeGraphManager()
        await kg_manager.initialize()
    
    # Initialize MJ client if not provided
    if not mj_client:
        mj_client = MidjourneyClient()
    
    return PersonaBatchGenerator(
        knowledge_graph=kg_manager,
        midjourney_client=mj_client,
        max_concurrent=max_concurrent
    )
