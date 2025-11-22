"""
Image Ingestion Agent for Children's Book Swarm

Downloads images from GCS, generates embeddings, and stores in KG + Qdrant.

Date: 2025-01-08
Status: Implementation
"""

import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import uuid
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables (CRITICAL for API keys!)
load_dotenv()

try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound
except ImportError as e:
    storage = None
    NotFound = None
    logger.warning(f"Google Cloud Storage not available: {e}")

try:
    from integrations.google_cloud_auth import get_gcs_client
except ImportError:
    get_gcs_client = None
    logger.warning("Enhanced Google Cloud Storage auth not available")

from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from kg.services.image_embedding_service import ImageEmbeddingService
from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

# Namespaces
SCHEMA = Namespace("http://schema.org/")
KG = Namespace("http://example.org/kg#")
BOOK = Namespace("http://example.org/childrens-book#")
DC = Namespace("http://purl.org/dc/elements/1.1/")
PROJECT = Namespace("http://example.org/project/")


class ImageIngestionAgent(BaseAgent):
    """
    Agent responsible for downloading images from GCS and ingesting them into
    the knowledge graph with embeddings.
    
    Workflow:
    1. Download images from GCS (input_kids_monster/ and generated_images/)
    2. For each image:
       - Generate visual embedding using ImageEmbeddingService
       - Store in KG as schema:ImageObject with kg:hasEmbedding property
       - Store embedding in Qdrant for fast similarity search
       - Upload to GCS if not already there
    3. Log all operations to KG
    
    Reuses:
    - ImageEmbeddingService (Task 1)
    - KnowledgeGraphManager
    - User's GCS download pattern
    """
    
    def __init__(
        self,
        agent_id: str = "image_ingestion_agent",
        capabilities: Optional[set] = None,
        kg_manager: Optional[KnowledgeGraphManager] = None,
        embedding_service: Optional[ImageEmbeddingService] = None,
        gcs_bucket_name: Optional[str] = None,
        max_concurrent_downloads: int = 8,
    ):
        """
        Initialize the Image Ingestion Agent.
        
        Args:
            agent_id: Unique identifier for this agent
            capabilities: Set of capabilities this agent provides
            kg_manager: Knowledge graph manager instance
            embedding_service: Image embedding service instance
            gcs_bucket_name: GCS bucket name (defaults to env var)
        """
        super().__init__(
            agent_id=agent_id,
            capabilities=capabilities or {"image_ingestion", "gcs_download", "embedding_generation"}
        )
        
        # Initialize KG manager with persistent storage if not provided
        # This ensures images persist across runs
        self.kg_manager = kg_manager or KnowledgeGraphManager(persistent_storage=True)

        # Initialize embedding service (optional)
        if embedding_service is not None:
            self.embedding_service = embedding_service
        elif embedding_service is not False:  # Allow explicit None to disable
            try:
                self.embedding_service = ImageEmbeddingService()
            except Exception as e:
                logger.warning(f"Could not initialize ImageEmbeddingService: {e}")
                self.embedding_service = None
        else:
            self.embedding_service = None
        
        # Initialize GCS client with enhanced authentication
        self.gcs_bucket_name = gcs_bucket_name or os.getenv("GCS_BUCKET_NAME", "veo-videos-baro-1759717316")

        if storage is None:
            raise ImportError("Google Cloud Storage required. Install with: pip install google-cloud-storage")
        self.max_concurrent_downloads = max(1, max_concurrent_downloads)
        self._download_semaphore: Optional[asyncio.Semaphore] = None

        # Initialize GCS client later in async initialize() method
        self.gcs_client = None
        self.gcs_bucket = None
        self.enhanced_auth = False

    async def initialize(self) -> None:
        """Async initialization of the agent."""
        await super().initialize()
        # Try enhanced authentication first, fall back to basic
        if get_gcs_client:
            try:
                self.gcs_client = await get_gcs_client()
                self.enhanced_auth = True
                logger.info("Using enhanced Google Cloud Storage authentication")
            except Exception as e:
                logger.warning(f"Enhanced GCS authentication failed: {e}, falling back to basic auth")
                self.enhanced_auth = False
        else:
            self.enhanced_auth = False
            logger.info("Enhanced GCS integration not available, using basic authentication")

        if not self.enhanced_auth:
            # Fallback to basic authentication
            project_id = os.getenv("GOOGLE_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "veo-gen-baro-1759717223"))
            self.gcs_client = storage.Client(project=project_id)

        self.gcs_bucket = self.gcs_client.bucket(self.gcs_bucket_name)
        self._download_semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

        logger.info(
            f"ImageIngestionAgent initialized: "
            f"bucket={self.gcs_bucket_name}, "
            f"capabilities={self.capabilities}, "
            f"max_concurrent_downloads={self.max_concurrent_downloads}"
        )
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """
        Process incoming messages to download and ingest images.
        
        Expected message content:
        {
            "action": "ingest_images",
            "input_prefix": "input_kids_monster/",
            "output_prefix": "generated_images/",
            "local_input_dir": "downloads/input_kids_monster/",
            "local_output_dir": "downloads/generated_images/",
            "extensions": ["png", "jpg"],  # optional
            "overwrite": false  # optional
        }
        
        Returns:
            AgentMessage with results:
            {
                "status": "success",
                "input_images_count": 10,
                "output_images_count": 50,
                "total_embeddings_generated": 60,
                "input_image_uris": [...],
                "output_image_uris": [...]
            }
        """
        action = message.content.get("action")
        
        if action == "ingest_images":
            return await self._handle_ingest_images(message)
        elif action == "ingest_local_folder":
            return await self._handle_ingest_local_folder(message)
        else:
            return self._create_error_response(
                message.sender_id,
                f"Unknown action: {action}"
            )
    
    async def _handle_ingest_images(self, message: AgentMessage) -> AgentMessage:
        """Handle the ingest_images action."""
        try:
            # Extract parameters
            input_prefix = message.content.get("input_prefix", "input_kids_monster/")
            output_prefix = message.content.get("output_prefix", "generated_images/")
            local_input_dir = Path(message.content.get("local_input_dir", "downloads/input_kids_monster/"))
            local_output_dir = Path(message.content.get("local_output_dir", "downloads/generated_images/"))
            extensions = message.content.get("extensions", ["png", "jpg", "jpeg"])
            overwrite = message.content.get("overwrite", False)
            project_id = message.content.get("project_id")  # Optional project tag
            
            logger.info(f"Starting image ingestion: input={input_prefix}, output={output_prefix}")
            if project_id:
                logger.info(f"Tagging images with project: {project_id}")
            logger.info(f"Bucket: {self.gcs_bucket_name}, Local dirs: input={local_input_dir}, output={local_output_dir}")
            
            # Download and ingest input images
            input_uris = await self._download_and_ingest_folder(
                prefix=input_prefix,
                local_dir=local_input_dir,
                image_type="input",
                extensions=extensions,
                overwrite=overwrite,
                project_id=project_id
            )
            
            # Download and ingest output images
            output_uris = await self._download_and_ingest_folder(
                prefix=output_prefix,
                local_dir=local_output_dir,
                image_type="output",
                extensions=extensions,
                overwrite=overwrite,
                project_id=project_id
            )
            
            total_count = len(input_uris) + len(output_uris)
            
            # Log detailed results
            logger.info(
                f"Image ingestion complete: "
                f"inputs={len(input_uris)}, outputs={len(output_uris)}, total={total_count}"
            )
            
            # Warn if no images found
            if total_count == 0:
                logger.warning(
                    f"No images ingested. Check: "
                    f"bucket={self.gcs_bucket_name}, "
                    f"input_prefix={input_prefix}, "
                    f"output_prefix={output_prefix}, "
                    f"extensions={extensions}"
                )
            
            # Create response
            response_content = {
                "status": "success",
                "input_images_count": len(input_uris),
                "output_images_count": len(output_uris),
                "total_embeddings_generated": total_count,
                "input_image_uris": input_uris,
                "output_image_uris": output_uris,
            }
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=response_content,
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error in ingest_images: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))

    async def _handle_ingest_local_folder(self, message: AgentMessage) -> AgentMessage:
        """
        Handle the ingest_local_folder action.
        Uploads local images to GCS and ingests them.
        """
        try:
            local_dir = Path(message.content.get("local_dir", "uploads"))
            gcs_prefix = message.content.get("gcs_prefix", "uploads/")
            image_type = message.content.get("image_type", "input")
            extensions = message.content.get("extensions", ["png", "jpg", "jpeg"])
            project_id = message.content.get("project_id")
            
            logger.info(f"Starting local ingestion from {local_dir} to gs://{self.gcs_bucket_name}/{gcs_prefix}")
            
            if not local_dir.exists():
                return self._create_error_response(message.sender_id, f"Local directory not found: {local_dir}")

            uris = await self._ingest_local_folder(
                local_dir=local_dir,
                gcs_prefix=gcs_prefix,
                image_type=image_type,
                extensions=extensions,
                project_id=project_id
            )
            
            response_content = {
                "status": "success",
                "ingested_count": len(uris),
                "image_uris": uris,
                "local_dir": str(local_dir),
                "project_id": project_id
            }
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=response_content,
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error in ingest_local_folder: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))

    async def _ingest_local_folder(
        self,
        local_dir: Path,
        gcs_prefix: str,
        image_type: str,
        extensions: List[str],
        project_id: Optional[str] = None
    ) -> List[str]:
        """
        Ingest all images from a local directory.
        """
        normalized_extensions = tuple(ext.lower().lstrip('.') for ext in extensions)
        files = []
        for ext in normalized_extensions:
            files.extend(local_dir.glob(f"*.{ext}"))
            # Add uppercase versions too just in case
            files.extend(local_dir.glob(f"*.{ext.upper()}"))
            
        # Deduplicate based on path
        files = list(set(files))
        
        logger.info(f"Found {len(files)} images in {local_dir}")
        
        image_uris = []
        batch_size = 10
        
        semaphore = self._download_semaphore or asyncio.Semaphore(self.max_concurrent_downloads)

        async def throttled_ingest(file_path):
            async with semaphore:
                return await self._upload_and_ingest_image(
                    local_path=file_path,
                    gcs_prefix=gcs_prefix,
                    image_type=image_type,
                    project_id=project_id
                )

        # Batch process
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            tasks = [throttled_ingest(f) for f in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Error ingesting {res}")
                elif res:
                    image_uris.append(res)
                    
        return image_uris

    async def _upload_and_ingest_image(
        self,
        local_path: Path,
        gcs_prefix: str,
        image_type: str,
        project_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload a local file to GCS and ingest it.
        """
        filename = local_path.name
        blob_name = f"{gcs_prefix.rstrip('/')}/{filename}"
        blob = self.gcs_bucket.blob(blob_name)
        
        # Upload if not exists
        if not blob.exists():
            logger.info(f"Uploading {filename} to {blob_name}")
            try:
                blob.upload_from_filename(str(local_path))
            except Exception as e:
                logger.error(f"Failed to upload {filename}: {e}")
                return None
        
        # Generate embedding
        try:
            embedding, description = await self.embedding_service.embed_image(local_path)
        except Exception as e:
            logger.error(f"Failed to generate embedding for {filename}: {e}")
            return None
            
        gcs_url = f"gs://{self.gcs_bucket_name}/{blob_name}"
        image_uri = f"http://example.org/image/{uuid.uuid4()}"
        
        # Store in KG
        try:
            await self._store_image_in_kg(
                image_uri=image_uri,
                filename=filename,
                gcs_url=gcs_url,
                image_type=image_type,
                embedding=embedding,
                description=description,
                file_size=local_path.stat().st_size,
                project_id=project_id
            )
        except Exception as e:
            logger.error(f"Failed to store {filename} in KG: {e}")
            return None
            
        # Store embedding in Qdrant
        try:
            self.embedding_service.store_embedding(
                image_uri=image_uri,
                embedding=embedding,
                metadata={
                    "filename": filename,
                    "gcs_url": gcs_url,
                    "image_type": image_type,
                    "description": description,
                }
            )
        except Exception as e:
            logger.error(f"Failed to store embedding for {filename}: {e}")
        
        return image_uri

    async def _download_and_ingest_folder(
        self,
        prefix: str,
        local_dir: Path,
        image_type: str,  # "input" or "output"
        extensions: List[str],
        overwrite: bool = False,
        project_id: Optional[str] = None,
    ) -> List[str]:
        """
        Download images from GCS folder and ingest into KG + Qdrant.
        
        Args:
            prefix: GCS folder prefix
            local_dir: Local directory to download to
            image_type: "input" or "output"
            extensions: List of allowed file extensions
            overwrite: Whether to overwrite existing files
        
        Returns:
            List of image URIs created in the KG
        """
        # Ensure directory exists
        local_dir.mkdir(parents=True, exist_ok=True)
        
        # List blobs in GCS
        try:
            blobs = self._list_blobs(prefix, extensions)
        except Exception as e:
            logger.error(f"Failed to list blobs in gs://{self.gcs_bucket_name}/{prefix}: {e}")
            return []  # Return empty list on error
        
        # Map image_type to display name
        type_display = "Input" if image_type.lower() == "input" else "Output"
        
        # Process ALL images - no limits (user requested all 4000+ images)
        # Previously limited to: 15 inputs, 180 outputs
        # Now processing everything for complete KG/Qdrant population
        logger.info(f"Processing all {len(blobs)} {type_display} images (no limit)")
        
        if len(blobs) == 0:
            logger.warning(
                f"No {type_display.lower()} images found in gs://{self.gcs_bucket_name}/{prefix} "
                f"with extensions {extensions}. Check prefix and bucket permissions."
            )
        else:
            logger.info(f"Found {len(blobs)} {type_display.lower()} images in gs://{self.gcs_bucket_name}/{prefix}")
        
        # Download and ingest each image IN PARALLEL (batches of 10)
        image_uris = []
        batch_size = 10
        total_batches = (len(blobs) + batch_size - 1) // batch_size
        
        # Wrap batch processing with tqdm
        semaphore = self._download_semaphore or asyncio.Semaphore(self.max_concurrent_downloads)

        async def throttled_download(blob_obj):
            async with semaphore:
                return await self._download_and_ingest_image(
                    blob=blob_obj,
                    local_dir=local_dir,
                    image_type=image_type,
                    overwrite=overwrite,
                    project_id=project_id
                )

        with tqdm(
            total=len(blobs),
            desc=f"Processing {type_display} images",
            unit="img",
            ncols=100,
            colour="cyan"
        ) as pbar:
            for i in range(0, len(blobs), batch_size):
                batch = blobs[i:i + batch_size]
                batch_num = i//batch_size + 1
                pbar.set_description(f"Processing {type_display} images [batch {batch_num}/{total_batches}]")

                tasks = [throttled_download(blob) for blob in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                successful = 0
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch processing error: {result}")
                    elif result:
                        image_uris.append(result)
                        successful += 1

                pbar.update(len(batch))
                pbar.set_postfix({"successful": len(image_uris), "failed": len(batch) - successful})
        
        return image_uris
    
    def _list_blobs(self, prefix: str, extensions: List[str]) -> List[Any]:
        """List all image blobs in a GCS folder."""
        normalized_extensions = tuple(ext.lower().lstrip('.') for ext in extensions)
        
        blobs = []
        for blob in self.gcs_bucket.list_blobs(prefix=prefix):
            # Skip directories
            if blob.name.endswith('/'):
                continue
            
            # Filter by extension
            suffix = Path(blob.name).suffix.lower().lstrip('.')
            if suffix not in normalized_extensions:
                continue
            
            blobs.append(blob)
        
        return blobs
    
    async def _download_and_ingest_image(
        self,
        blob: Any,
        local_dir: Path,
        image_type: str,
        overwrite: bool,
        project_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Download a single image from GCS and ingest it into KG + Qdrant.
        
        Args:
            blob: GCS blob object
            local_dir: Local directory to download to
            image_type: "input" or "output"
            overwrite: Whether to overwrite existing files
            project_id: Optional project identifier to tag image with
        
        Returns:
            The image URI in the KG, or None if failed
        """
        # Determine local path
        filename = Path(blob.name).name
        local_path = local_dir / filename
        
        # Download if needed
        if local_path.exists() and not overwrite:
            logger.debug(f"Skipping {filename} (already exists)")
        else:
            try:
                blob.download_to_filename(str(local_path))
                logger.info(f"Downloaded {filename} ({blob.size} bytes)")
            except NotFound:
                logger.error(f"Blob not found: {blob.name}")
                return None
            except Exception as e:
                logger.error(f"Failed to download {blob.name}: {e}")
                return None
        
        # Generate embedding
        try:
            embedding, description = await self.embedding_service.embed_image(local_path)
        except Exception as e:
            logger.error(f"Failed to generate embedding for {filename}: {e}")
            return None
        
        # Create GCS URL
        gcs_url = f"gs://{self.gcs_bucket_name}/{blob.name}"
        
        # Create image URI
        image_uri = f"http://example.org/image/{uuid.uuid4()}"
        
        # Store in KG
        try:
            await self._store_image_in_kg(
                image_uri=image_uri,
                filename=filename,
                gcs_url=gcs_url,
                image_type=image_type,
                embedding=embedding,
                description=description,
                file_size=blob.size,
                project_id=project_id
            )
        except Exception as e:
            logger.error(f"Failed to store {filename} in KG: {e}")
            return None
        
        # Store embedding in Qdrant
        try:
            self.embedding_service.store_embedding(
                image_uri=image_uri,
                embedding=embedding,
                metadata={
                    "filename": filename,
                    "gcs_url": gcs_url,
                    "image_type": image_type,
                    "description": description,
                }
            )
        except Exception as e:
            logger.error(f"Failed to store embedding for {filename}: {e}")
            # Continue anyway - KG data is more important
        
        logger.debug(f"Ingested {filename} as {image_uri}")
        return image_uri
    
    async def _store_image_in_kg(
        self,
        image_uri: str,
        filename: str,
        gcs_url: str,
        image_type: str,
        embedding: List[float],
        description: str,
        file_size: int,
        project_id: Optional[str] = None
    ) -> None:
        """
        Store an image in the knowledge graph.
        
        Args:
            image_uri: Unique URI for the image in KG
            filename: Original filename
            gcs_url: GCS URL (gs://bucket/path)
            image_type: "input" or "output"
            embedding: Embedding vector (for dimension calculation)
            description: AI-generated description
            file_size: File size in bytes
            project_id: Optional project identifier to tag image with
        """
        image_ref = URIRef(image_uri)
        
        # Determine class based on image type
        if image_type == "input":
            image_class = BOOK.InputImage
        elif image_type == "output":
            image_class = BOOK.OutputImage
        else:
            image_class = SCHEMA.ImageObject
        
        # Add triples
        triples = [
            # Type
            (image_ref, RDF.type, image_class),
            (image_ref, RDF.type, SCHEMA.ImageObject),
            
            # Basic properties
            (image_ref, SCHEMA.name, Literal(filename)),
            (image_ref, SCHEMA.contentUrl, Literal(gcs_url)),
            (image_ref, DC.created, Literal(datetime.utcnow().isoformat(), datatype=XSD.dateTime)),
            
            # Image-specific properties
            (image_ref, KG.imageType, Literal(image_type)),
            (image_ref, SCHEMA.contentSize, Literal(file_size, datatype=XSD.integer)),
            (image_ref, SCHEMA.description, Literal(description)),
            
            # ISSUE #6 FIX: Don't store full embedding in KG (too large, inefficient)
            # Instead, store a flag that embedding exists in Qdrant
            # The actual embedding is retrieved from Qdrant when needed via image_uri
            (image_ref, KG.hasEmbedding, Literal("true")),  # Flag: embedding exists
            (image_ref, KG.embeddingDimension, Literal(len(embedding), datatype=XSD.integer)),
            (image_ref, KG.embeddingStorage, Literal("qdrant")),  # Where embedding is stored
        ]
        
        # Add project tag if provided
        if project_id:
            project_uri = URIRef(f"{PROJECT}{project_id}")
            # Link image to project
            triples.append((image_ref, KG.relatedToProject, project_uri))
            # Also ensure project node exists (type declaration)
            triples.append((project_uri, RDF.type, PROJECT.Project))
        
        # Add to KG
        # Convert URIRef/Literal objects to strings for add_triple
        for triple in triples:
            subj, pred, obj = triple
            # Convert URIRef/Literal to strings
            subj_str = str(subj) if hasattr(subj, '__str__') else subj
            pred_str = str(pred) if hasattr(pred, '__str__') else pred
            # Keep Literal objects as-is (they'll be handled by add_triple)
            obj_val = obj if isinstance(obj, Literal) else (str(obj) if hasattr(obj, '__str__') else obj)
            await self.kg_manager.add_triple(subj_str, pred_str, obj_val)
        
        logger.debug(f"Stored {filename} in KG with {len(triples)} triples")
    
    async def get_ingested_images(
        self,
        image_type: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query the KG for ingested images.
        
        Args:
            image_type: Filter by "input" or "output", or None for all
            project_id: Filter by project ID (will be sanitized for SPARQL safety)

        Returns:
            List of image dictionaries
        """
        # Sanitize project_id to prevent SPARQL injection
        if project_id:
            import re
            # Only allow alphanumeric, underscores, and hyphens
            sanitized_project_id = re.sub(r'[^a-zA-Z0-9_-]', '_', project_id)
            project_id = sanitized_project_id
        """
        Query the KG for ingested images.
        
        Args:
            image_type: Filter by "input" or "output", or None for all
            project_id: Filter by project identifier, or None for all projects
        
        Returns:
            List of image metadata dicts with uri, name, url, type, description, project_id
        """
        # Build query with optional filters
        type_filter = f'FILTER (?type = "{image_type}")' if image_type else ''
        project_filter = ''
        project_select = ''
        
        if project_id:
            project_uri = f"http://example.org/project/{project_id}"
            project_filter = f'?image kg:relatedToProject <{project_uri}> .'
            project_select = '?project'
        
        query = f"""
        PREFIX schema: <http://schema.org/>
        PREFIX kg: <http://example.org/kg#>
        PREFIX book: <http://example.org/childrens-book#>
        PREFIX project: <http://example.org/project/>
        
        SELECT ?image ?name ?url ?type ?description {project_select} WHERE {{
            ?image a schema:ImageObject ;
                   schema:name ?name ;
                   schema:contentUrl ?url ;
                   kg:imageType ?type .
            OPTIONAL {{ ?image schema:description ?description . }}
            {project_filter}
            {f'OPTIONAL {{ ?image kg:relatedToProject ?project . }}' if not project_id else ''}
            {type_filter}
        }}
        ORDER BY ?name
        """
        
        results = await self.kg_manager.query_graph(query)
        
        images = []
        for result in results:
            image_dict = {
                "uri": str(result["image"]),
                "name": str(result["name"]),
                "url": str(result["url"]),
                "type": str(result["type"]),
                "description": str(result.get("description", "")),
            }
            # Extract project_id from project URI if present
            if "project" in result and result["project"]:
                project_uri = str(result["project"])
                # Extract project ID from URI (e.g., "http://example.org/project/book_123" -> "book_123")
                if "/project/" in project_uri:
                    image_dict["project_id"] = project_uri.split("/project/")[-1]
            elif project_id:
                # If we're filtering by project_id, all results belong to that project
                image_dict["project_id"] = project_id
            images.append(image_dict)
        
        return images


# Standalone function for CLI use
async def ingest_images_from_gcs(
    input_prefix: str = "input_kids_monster/",
    output_prefix: str = "generated_images/",
    local_input_dir: str = "downloads/input_kids_monster/",
    local_output_dir: str = "downloads/generated_images/",
    extensions: Optional[List[str]] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to ingest images from GCS.
    
    Args:
        input_prefix: GCS prefix for input images
        output_prefix: GCS prefix for output images
        local_input_dir: Local directory for input images
        local_output_dir: Local directory for output images
        extensions: List of file extensions to download
        overwrite: Whether to overwrite existing files
    
    Returns:
        Dict with ingestion results
    """
    agent = ImageIngestionAgent()
    
    message = AgentMessage(
        sender_id="cli",
        recipient_id="image_ingestion_agent",
        content={
            "action": "ingest_images",
            "input_prefix": input_prefix,
            "output_prefix": output_prefix,
            "local_input_dir": local_input_dir,
            "local_output_dir": local_output_dir,
            "extensions": extensions or ["png", "jpg", "jpeg"],
            "overwrite": overwrite,
        },
        message_type="request",
        timestamp=datetime.utcnow().isoformat()
    )
    
    response = await agent._process_message_impl(message)
    return response.content

