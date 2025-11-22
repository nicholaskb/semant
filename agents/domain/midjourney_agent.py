"""
MidjourneyAgent - Agent wrapper for Midjourney image generation services
========================================================================
Provides a BaseAgent-compatible interface to Midjourney functionality.
"""

from typing import Dict, Any, List, Optional, Set
import asyncio
import uuid
from datetime import datetime
import json

from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.agent_registry import AgentRegistry
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger

# Import Midjourney components
try:
    from midjourney_integration.client import MidjourneyClient, poll_until_complete, upload_to_gcs_and_get_public_url
    from semant.agent_tools.midjourney.workflows import (
        imagine_then_mirror,
        generate_themed_portraits
    )
    from midjourney_integration.persona_batch_generator import PersonaBatchGenerator
    MIDJOURNEY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Midjourney components not available: {e}")
    MIDJOURNEY_AVAILABLE = False


class MidjourneyAgent(BaseAgent):
    """
    Agent that provides Midjourney image generation capabilities.
    
    Capabilities:
    - IMAGE_GENERATION: Generate images from text prompts
    - IMAGE_DESCRIPTION: Describe images using AI
    - IMAGE_BLENDING: Blend multiple images together
    - IMAGE_VARIATION: Create variations of existing images
    - BATCH_GENERATION: Generate batches of themed images
    - IMAGE_UPLOAD: Upload images to cloud storage
    """
    
    # Define agent capabilities as Capability objects
    @property
    def CAPABILITIES(self):
        from agents.core.capability_types import Capability, CapabilityType
        return {
            Capability(type=CapabilityType.IMAGE_GENERATION, version="1.0"),
            Capability(type=CapabilityType.IMAGE_DESCRIPTION, version="1.0"),
            Capability(type=CapabilityType.IMAGE_BLENDING, version="1.0"),
            Capability(type=CapabilityType.IMAGE_VARIATION, version="1.0"),
            Capability(type=CapabilityType.BATCH_GENERATION, version="1.0"),
            Capability(type=CapabilityType.IMAGE_UPLOAD, version="1.0")
        }
    
    def __init__(
        self,
        agent_id: str = "midjourney_agent",
        registry: Optional[AgentRegistry] = None,
        knowledge_graph: Optional[KnowledgeGraphManager] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Midjourney agent.
        
        Args:
            agent_id: Unique identifier for this agent
            registry: Optional agent registry for discovery
            knowledge_graph: Optional KG for tracking operations
            config: Optional configuration dictionary
        """
        # Initialize with capabilities (already Capability objects)
        super().__init__(
            agent_id=agent_id,
            capabilities=self.CAPABILITIES,
            config=config or {}
        )
        
        self.registry = registry
        self.kg = knowledge_graph
        self.mj_client = None
        self.batch_generator = None
        
        # Initialize Midjourney components if available
        if MIDJOURNEY_AVAILABLE:
            try:
                self.mj_client = MidjourneyClient()
                if self.kg:
                    self.batch_generator = PersonaBatchGenerator(
                        knowledge_graph=self.kg,
                        midjourney_client=self.mj_client,
                        max_concurrent=3
                    )
                logger.info(f"MidjourneyAgent initialized: {agent_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Midjourney components: {e}")
                self.mj_client = None
                self.batch_generator = None
        
        # Register with registry if provided
        if self.registry:
            asyncio.create_task(self._register_with_registry())
    
    async def _register_with_registry(self):
        """Register this agent with the agent registry."""
        try:
            await self.registry.register_agent(self)
            logger.info(f"MidjourneyAgent {self.agent_id} registered with registry")
        except Exception as e:
            logger.error(f"Failed to register with registry: {e}")
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """
        Process incoming messages requesting Midjourney operations.
        
        Args:
            message: Incoming agent message with operation request
            
        Returns:
            Response message with operation results
        """
        if not MIDJOURNEY_AVAILABLE or not self.mj_client:
            return self._create_error_response(
                message,
                "Midjourney components not available"
            )
        
        # Extract operation type and parameters
        content = message.content
        operation = content.get("operation", "generate")
        
        try:
            # Route to appropriate handler
            if operation == "generate" or operation == "imagine":
                return await self._handle_generation(message)
            elif operation == "describe":
                return await self._handle_description(message)
            elif operation == "blend":
                return await self._handle_blending(message)
            elif operation == "variation":
                return await self._handle_variation(message)
            elif operation == "batch":
                return await self._handle_batch_generation(message)
            elif operation == "upload":
                return await self._handle_upload(message)
            else:
                return self._create_error_response(
                    message,
                    f"Unknown operation: {operation}"
                )
                
        except Exception as e:
            logger.error(f"Error processing Midjourney operation: {e}")
            return self._create_error_response(message, str(e))
    
    async def _handle_generation(self, message: AgentMessage) -> AgentMessage:
        """Handle image generation requests."""
        content = message.content
        prompt = content.get("prompt", "")
        
        if not prompt:
            return self._create_error_response(message, "Prompt required for generation")
        
        # Extract optional parameters
        version = content.get("version", "v6")
        aspect_ratio = content.get("aspect_ratio", "1:1")
        process_mode = content.get("process_mode", "relax")
        cref = content.get("cref")
        cw = content.get("cw")
        oref = content.get("oref")
        ow = content.get("ow")
        
        logger.info(f"Generating image: {prompt[:50]}...")
        
        try:
            # Use imagine_then_mirror workflow for complete process
            result = await imagine_then_mirror(
                prompt=prompt,
                version=version,
                aspect_ratio=aspect_ratio,
                process_mode=process_mode,
                cref=cref,
                cw=cw,
                oref=oref,
                ow=ow,
                poll_interval=5.0,
                poll_timeout=900
            )
            
            # Store in KG if available
            if self.kg:
                await self._store_generation_in_kg(prompt, result)
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "success": True,
                    "operation": "generate",
                    "prompt": prompt,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                },
                message_type="response"
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return self._create_error_response(message, f"Generation failed: {e}")
    
    async def _handle_description(self, message: AgentMessage) -> AgentMessage:
        """Handle image description requests."""
        content = message.content
        image_url = content.get("image_url")
        image_file = content.get("image_file")
        
        if not image_url and not image_file:
            return self._create_error_response(
                message,
                "Either image_url or image_file required for description"
            )
        
        try:
            # Upload file if provided
            if image_file and not image_url:
                image_url = await self._upload_image(image_file)
            
            # Submit describe task
            response = await self.mj_client.submit_describe(image_url)
            task_id = response.get("data", {}).get("task_id")
            
            if not task_id:
                raise Exception("No task_id received from describe")
            
            # Poll for result
            result = await poll_until_complete(
                client=self.mj_client,
                task_id=task_id,
                kg_manager=self.kg
            )
            
            description = result.get("output", {}).get("description", "")
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "success": True,
                    "operation": "describe",
                    "image_url": image_url,
                    "description": description,
                    "timestamp": datetime.now().isoformat()
                },
                message_type="response"
            )
            
        except Exception as e:
            logger.error(f"Description failed: {e}")
            return self._create_error_response(message, f"Description failed: {e}")
    
    async def _handle_blending(self, message: AgentMessage) -> AgentMessage:
        """Handle image blending requests."""
        content = message.content
        image_urls = content.get("image_urls", [])
        dimension = content.get("dimension", "1:1")
        
        if len(image_urls) < 2 or len(image_urls) > 5:
            return self._create_error_response(
                message,
                "Blend requires 2 to 5 images"
            )
        
        try:
            # Submit blend task
            response = await self.mj_client.submit_blend(image_urls, dimension)
            task_id = response.get("data", {}).get("task_id")
            
            if not task_id:
                raise Exception("No task_id received from blend")
            
            # Poll for result
            result = await poll_until_complete(
                client=self.mj_client,
                task_id=task_id,
                kg_manager=self.kg
            )
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "success": True,
                    "operation": "blend",
                    "image_urls": image_urls,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                },
                message_type="response"
            )
            
        except Exception as e:
            logger.error(f"Blending failed: {e}")
            return self._create_error_response(message, f"Blending failed: {e}")
    
    async def _handle_variation(self, message: AgentMessage) -> AgentMessage:
        """Handle image variation requests."""
        content = message.content
        original_task_id = content.get("task_id")
        button = content.get("button", "V1")  # V1, V2, V3, V4
        
        if not original_task_id:
            return self._create_error_response(
                message,
                "Task ID required for variation"
            )
        
        try:
            # Submit variation action
            response = await self.mj_client.submit_action(
                action=button,
                task_id=original_task_id
            )
            
            new_task_id = response.get("data", {}).get("task_id")
            
            if not new_task_id:
                raise Exception("No task_id received from variation")
            
            # Poll for result
            result = await poll_until_complete(
                client=self.mj_client,
                task_id=new_task_id,
                kg_manager=self.kg
            )
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "success": True,
                    "operation": "variation",
                    "original_task_id": original_task_id,
                    "button": button,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                },
                message_type="response"
            )
            
        except Exception as e:
            logger.error(f"Variation failed: {e}")
            return self._create_error_response(message, f"Variation failed: {e}")
    
    async def _handle_batch_generation(self, message: AgentMessage) -> AgentMessage:
        """Handle batch generation requests."""
        if not self.batch_generator:
            return self._create_error_response(
                message,
                "Batch generator not available"
            )
        
        content = message.content
        persona_images = content.get("persona_images", [])
        theme = content.get("theme", "")
        batch_size = content.get("batch_size", 10)
        model_version = content.get("model_version")
        
        if len(persona_images) != 6:
            return self._create_error_response(
                message,
                "Exactly 6 persona images required for batch generation"
            )
        
        if not theme:
            return self._create_error_response(
                message,
                "Theme required for batch generation"
            )
        
        try:
            result = await self.batch_generator.generate_themed_batch(
                persona_images=persona_images,
                theme_prompt=theme,
                batch_size=batch_size,
                model_version=model_version
            )
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "success": result["success"],
                    "operation": "batch",
                    "batch_id": result["batch_id"],
                    "theme": theme,
                    "total_generated": result["total_generated"],
                    "generated_images": result["generated_images"],
                    "errors": result.get("errors", []),
                    "timestamp": datetime.now().isoformat()
                },
                message_type="response"
            )
            
        except Exception as e:
            logger.error(f"Batch generation failed: {e}")
            return self._create_error_response(message, f"Batch generation failed: {e}")
    
    async def _handle_upload(self, message: AgentMessage) -> AgentMessage:
        """Handle image upload requests."""
        content = message.content
        image_file = content.get("image_file")
        image_content = content.get("image_content")
        filename = content.get("filename", f"{uuid.uuid4()}.png")
        content_type = content.get("content_type", "image/png")
        
        if not image_file and not image_content:
            return self._create_error_response(
                message,
                "Either image_file or image_content required for upload"
            )
        
        try:
            # Get content to upload
            if image_content:
                file_content = image_content
            else:
                # Assume image_file is a file path or file-like object
                if isinstance(image_file, str):
                    with open(image_file, 'rb') as f:
                        file_content = f.read()
                else:
                    file_content = image_file.read()
            
            # Upload to GCS
            public_url = upload_to_gcs_and_get_public_url(
                file_content,
                filename,
                content_type
            )
            
            # Store in KG if available
            if self.kg:
                await self._store_upload_in_kg(filename, public_url)
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "success": True,
                    "operation": "upload",
                    "filename": filename,
                    "url": public_url,
                    "timestamp": datetime.now().isoformat()
                },
                message_type="response"
            )
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return self._create_error_response(message, f"Upload failed: {e}")
    
    async def _upload_image(self, image_file: Any) -> str:
        """Helper to upload an image and return its public URL."""
        filename = f"{uuid.uuid4()}.png"
        
        if isinstance(image_file, str):
            with open(image_file, 'rb') as f:
                file_content = f.read()
        else:
            file_content = image_file.read()
        
        return upload_to_gcs_and_get_public_url(
            file_content,
            filename,
            "image/png"
        )
    
    async def _store_generation_in_kg(self, prompt: str, result: Dict[str, Any]):
        """Store generation results in Knowledge Graph."""
        if not self.kg:
            return
        
        generation_id = f"generation_{uuid.uuid4().hex[:8]}"
        generation_uri = f"http://example.org/generation/{generation_id}"
        
        await self.kg.add_triple(
            generation_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ImageGeneration"
        )
        
        await self.kg.add_triple(
            generation_uri,
            "http://example.org/prompt",
            prompt
        )
        
        if result.get("task_id"):
            await self.kg.add_triple(
                generation_uri,
                "http://example.org/taskId",
                result["task_id"]
            )
        
        if result.get("image_url"):
            await self.kg.add_triple(
                generation_uri,
                "http://example.org/imageUrl",
                result["image_url"]
            )
        
        await self.kg.add_triple(
            generation_uri,
            "http://example.org/timestamp",
            datetime.now().isoformat()
        )
    
    async def _store_upload_in_kg(self, filename: str, url: str):
        """Store upload information in Knowledge Graph."""
        if not self.kg:
            return
        
        upload_id = f"upload_{uuid.uuid4().hex[:8]}"
        upload_uri = f"http://example.org/upload/{upload_id}"
        
        await self.kg.add_triple(
            upload_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ImageUpload"
        )
        
        await self.kg.add_triple(
            upload_uri,
            "http://example.org/filename",
            filename
        )
        
        await self.kg.add_triple(
            upload_uri,
            "http://example.org/url",
            url
        )
        
        await self.kg.add_triple(
            upload_uri,
            "http://example.org/timestamp",
            datetime.now().isoformat()
        )
    
    def _create_error_response(self, message: AgentMessage, error: str) -> AgentMessage:
        """Create an error response message."""
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={
                "success": False,
                "error": error,
                "original_request": message.content,
                "timestamp": datetime.now().isoformat()
            },
            message_type="error"
        )
    
    async def get_capabilities(self) -> Set[str]:
        """Return the agent's capabilities."""
        return self.CAPABILITIES
    
    async def shutdown(self):
        """Clean shutdown of the agent."""
        logger.info(f"Shutting down MidjourneyAgent {self.agent_id}")
        
        # Unregister from registry if registered
        if self.registry:
            try:
                await self.registry.unregister_agent(self.agent_id)
            except Exception as e:
                logger.error(f"Error unregistering from registry: {e}")
        
        # Close any open connections
        if self.mj_client and hasattr(self.mj_client, 'close'):
            await self.mj_client.close()
        
        await super().shutdown()
