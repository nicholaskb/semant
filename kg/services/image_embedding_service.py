"""
Image Embedding Service for Children's Book Swarm
Extends the pattern from agents/diary/diary_agent.py

This service generates embeddings for images and stores them in both:
1. Knowledge Graph (as kg:hasEmbedding property on schema:ImageObject)
2. Qdrant vector database (for fast similarity search)

Date: 2025-01-08
Status: Initial Implementation
"""

import asyncio
import base64
import hashlib
import io
import os
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image as PILImage
from loguru import logger
from dotenv import load_dotenv

# Clustering imports (optional - will fail gracefully if not available)
try:
    import numpy as np
    from sklearn.cluster import DBSCAN
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False
    logger.warning("scikit-learn not available - clustering features disabled. Install with: pip install scikit-learn")

# Load environment variables (CRITICAL for API keys!)
load_dotenv()

try:
    from openai import OpenAI
except ImportError as exc:
    OpenAI = None
    logger.warning("OpenAI library not available: %s", exc)

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError as exc:
    QdrantClient = None
    Distance = None
    VectorParams = None
    PointStruct = None
    logger.warning("Qdrant client not available: %s", exc)

# Constants (matching DiaryAgent pattern)
EMBEDDING_MODEL = "text-embedding-3-large"  # 1536 dimensions
EMBEDDING_DIMENSION = 1536
COLLECTION_NAME = "childrens_book_images"
LEGACY_POINT_ID_MOD = 2**63


def generate_stable_point_id(image_uri: str) -> str:
    """
    Generate a deterministic Qdrant point ID for an image URI.

    Uses SHA-256 to ensure stability across Python processes and avoids relying
    on the built-in hash() function (which is salted per process).
    
    Converts the SHA-256 hash to UUID format (required by Qdrant).

    Args:
        image_uri: The URI of the image in the KG.

    Returns:
        UUID-formatted string (8-4-4-4-12 hex characters with dashes).
    """
    if not image_uri:
        raise ValueError("image_uri is required to generate a point ID")
    normalized_uri = image_uri.strip()
    digest = hashlib.sha256(normalized_uri.encode("utf-8")).hexdigest()
    
    # Qdrant requires UUID format: convert first 32 hex chars to UUID format
    # Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    uuid_str = f"{digest[0:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"
    
    # Validate it's a valid UUID format
    try:
        uuid.UUID(uuid_str)
    except ValueError:
        # Fallback: use a deterministic UUID5 namespace
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
        uuid_str = str(uuid.uuid5(namespace, normalized_uri))
    
    return uuid_str


def generate_legacy_point_id(image_uri: str) -> int:
    """
    Generate the legacy numeric point ID that was previously used.

    This is retained for backward compatibility so we can still retrieve
    embeddings that were stored before the deterministic IDs were introduced.
    """
    if not image_uri:
        raise ValueError("image_uri is required to generate a legacy point ID")
    return hash(image_uri) % LEGACY_POINT_ID_MOD


class ImageEmbeddingService:
    """
    Service for generating and managing image embeddings.
    
    Reuses patterns from:
    - agents/diary/diary_agent.py: OpenAI embeddings + Qdrant integration
    - Uses text-embedding-3-large model (1536 dimensions)
    
    Features:
    - Generate embeddings from images (via visual description → text embedding)
    - Compute similarity between embeddings (cosine)
    - Store/retrieve embeddings in Qdrant
    - Link embeddings to KG nodes
    """
    
    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = COLLECTION_NAME,
    ):
        """
        Initialize the image embedding service.
        
        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            collection_name: Name of the Qdrant collection for image embeddings
        """
        if not OpenAI:
            raise ImportError("OpenAI library required. Install with: pip install openai")
        if not QdrantClient:
            raise ImportError("Qdrant client required. Install with: pip install qdrant-client")
        
        self._description_cache: Dict[Path, str] = {}
        self._embedding_cache: Dict[Path, List[float]] = {}

        # Initialize OpenAI client (reusing DiaryAgent pattern)
        self.openai_client = OpenAI()
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = collection_name
        
        # Create collection if it doesn't exist
        self._ensure_collection()
        
        logger.info(
            f"ImageEmbeddingService initialized: "
            f"collection={collection_name}, dimension={EMBEDDING_DIMENSION}"
        )
    
    def _ensure_collection(self) -> None:
        """Ensure the Qdrant collection exists for image embeddings."""
        try:
            self.qdrant_client.get_collection(self.collection_name)
            logger.debug(f"Collection '{self.collection_name}' already exists")
        except Exception:
            # Collection doesn't exist, create it
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection '{self.collection_name}'")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Create an embedding for text using OpenAI's embedding model.
        
        This is the same method from DiaryAgent - reused directly.
        
        Args:
            text: Text to embed
        
        Returns:
            List of 1536 floats representing the embedding
        """
        response = self.openai_client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL,
            dimensions=EMBEDDING_DIMENSION  # Explicitly request 1536 dimensions
        )
        
        # Validate response structure
        if not hasattr(response, 'data') or not response.data:
            raise ValueError("OpenAI embeddings API returned empty data")
        if len(response.data) == 0:
            raise ValueError("OpenAI embeddings API returned empty data array")
        if not hasattr(response.data[0], 'embedding') or not response.data[0].embedding:
            raise ValueError("OpenAI embeddings API returned invalid embedding structure")
        
        return response.data[0].embedding
    
    async def embed_image(
        self,
        image_path: Path,
        use_cached_description: Optional[str] = None,
    ) -> Tuple[List[float], str]:
        """
        Generate an embedding for an image.
        
        Strategy: Use GPT-4o vision to describe the image, then embed the description.
        This approach leverages:
        1. GPT-4o's visual understanding (like ImageAnalysisAgent)
        2. text-embedding-3-large for consistent vector space (1536-dim)
        
        Args:
            image_path: Path to the image file
            use_cached_description: If provided, skip vision API and use this description
        
        Returns:
            Tuple of (embedding_vector, image_description)
        """
        resolved_path = image_path.resolve()
        if use_cached_description:
            description = use_cached_description
            logger.debug(f"Using provided cached description for {image_path.name}")
        elif resolved_path in self._description_cache:
            description = self._description_cache[resolved_path]
            logger.debug(f"Using memoized description for {image_path.name}")
        else:
            # Generate image description using GPT-4o vision
            description = await self._describe_image_with_vision(image_path)
            self._description_cache[resolved_path] = description
        
        # Embed the description using TEXT embeddings (not vision embeddings)
        # This ensures we get 1536 dimensions, not 3072
        # Run in executor to avoid blocking event loop (enables true parallelism)
        def _call_embed_text():
            """Helper function for executor to call OpenAI embeddings API."""
            return self.embed_text(description)
        
        # Use get_running_loop() instead of get_event_loop() for async context
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Fallback if no running loop (shouldn't happen in async context)
            loop = asyncio.get_event_loop()
        if resolved_path in self._embedding_cache:
            logger.debug(f"Using memoized embedding for {image_path.name}")
            embedding = self._embedding_cache[resolved_path]
        else:
            embedding = await loop.run_in_executor(None, _call_embed_text)
        
        # Validate embedding
        if not embedding or not isinstance(embedding, list):
            raise ValueError("Embedding service returned invalid embedding")
        if len(embedding) == 0:
            raise ValueError("Embedding service returned empty embedding")
        
        # Verify dimension
        if len(embedding) != EMBEDDING_DIMENSION:
            logger.warning(f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(embedding)}")
            # Truncate or pad if needed
            if len(embedding) > EMBEDDING_DIMENSION:
                embedding = embedding[:EMBEDDING_DIMENSION]
            else:
                embedding = embedding + [0.0] * (EMBEDDING_DIMENSION - len(embedding))
        
        self._embedding_cache[resolved_path] = embedding
        logger.info(f"Generated embedding for {image_path.name} (dim={len(embedding)})")
        return embedding, description
    
    async def _describe_image_with_vision(self, image_path: Path) -> str:
        """
        Use GPT-4o vision to describe an image.
        
        Reuses pattern from agents/domain/image_analysis_agent.py
        but optimized for embedding generation.
        
        Args:
            image_path: Path to image
        
        Returns:
            Detailed description of the image
        """
        # Load and encode image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        # Convert to base64
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        
        # Detect actual image format and determine MIME type
        # CRITICAL FIX: Don't hardcode PNG - detect actual format
        try:
            with PILImage.open(image_path) as img:
                img_format = img.format
                if img_format:
                    # Map PIL format to MIME type
                    format_to_mime = {
                        "PNG": "image/png",
                        "JPEG": "image/jpeg",
                        "JPG": "image/jpeg",
                        "GIF": "image/gif",
                        "WEBP": "image/webp",
                        "BMP": "image/bmp",
                        "TIFF": "image/tiff",
                    }
                    mime_type = format_to_mime.get(img_format.upper(), "image/png")
                else:
                    # Format not detected, fallback to PNG
                    mime_type = "image/png"
                    logger.warning(f"Could not detect image format for {image_path.name}, defaulting to PNG")
        except Exception as e:
            # If PIL fails to open image, fallback to PNG
            mime_type = "image/png"
            logger.warning(f"Failed to detect image format for {image_path.name}: {e}, defaulting to PNG")
        
        # Prepare vision prompt (optimized for embedding)
        vision_prompt = """Describe this image in detail for similarity matching. Include:
        1. Main subjects (characters, objects, people)
        2. Actions and poses
        3. Colors and color palette
        4. Composition and layout
        5. Style and artistic approach
        6. Mood and atmosphere
        7. Any text or symbols visible
        
        Be specific and comprehensive."""
        
        # Run OpenAI call in executor to avoid blocking event loop (enables true parallelism)
        # Reusing pattern from midjourney_integration/client.py
        def _call_openai_vision():
            """Helper function for executor to call OpenAI vision API."""
            return self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": vision_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded_image}"
                            }
                        }
                    ]
                }],
                temperature=0.5,  # Lower temp for consistency
            )
        
        # Use get_running_loop() instead of get_event_loop() for async context
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Fallback if no running loop (shouldn't happen in async context)
            loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _call_openai_vision)
        
        # Validate response structure
        if not hasattr(response, 'choices') or not response.choices:
            raise ValueError("OpenAI vision API returned empty choices")
        if not hasattr(response.choices[0], 'message') or not response.choices[0].message:
            raise ValueError("OpenAI vision API returned invalid message structure")
        if not hasattr(response.choices[0].message, 'content') or not response.choices[0].message.content:
            raise ValueError("OpenAI vision API returned empty content")
        
        description = response.choices[0].message.content.strip()
        if not description:
            raise ValueError("OpenAI vision API returned empty description after stripping")
        
        logger.debug(f"Vision description: {description[:100]}...")
        
        return description
    
    @staticmethod
    def compute_similarity(emb1: List[float], emb2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            emb1: First embedding vector
            emb2: Second embedding vector
        
        Returns:
            Similarity score between -1 and 1 (1 = identical, 0 = orthogonal, -1 = opposite)
        """
        import numpy as np
        
        # Convert to numpy arrays
        vec1 = np.array(emb1)
        vec2 = np.array(emb2)
        
        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        return float(similarity)
    
    def store_embedding(
        self,
        image_uri: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store an image embedding in Qdrant.
        
        Args:
            image_uri: URI of the image in the knowledge graph (used as point ID)
            embedding: The embedding vector (1536 dimensions)
            metadata: Optional metadata to store with the embedding
        
        Returns:
            The point ID (image_uri)
        """
        if not image_uri:
            raise ValueError("image_uri is required to store an embedding")

        # Prepare metadata
        payload = dict(metadata) if metadata else {}
        payload["image_uri"] = image_uri
        payload.setdefault("point_id_version", "sha256-v1")

        point_id = generate_stable_point_id(image_uri)

        # Create point
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=payload,
        )
        
        # Upsert to Qdrant
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )
        
        logger.debug(f"Stored embedding for {image_uri}")
        return image_uri
    
    def search_similar_images(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar images using embedding similarity.
        
        Args:
            query_embedding: The query embedding vector
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score (0-1). 
                            If None or 0.0, no threshold is applied (all results returned).
                            Values > 0.0 filter results to only those with similarity >= threshold.
            filter_metadata: Optional filters on metadata fields
        
        Returns:
            List of results with format:
            [
                {
                    "image_uri": "...",
                    "score": 0.95,
                    "metadata": {...}
                },
                ...
            ]
        """
        # Prepare query filter if needed
        query_filter = None
        if filter_metadata:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filter_metadata.items()
            ]
            if conditions:
                query_filter = Filter(must=conditions)
        
        # Search
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )
        
        # Format results and add image_url field
        # CRITICAL: Always try to provide real URL, log when we can't
        formatted_results = []
        for result in results:
            image_uri = result.payload.get("image_uri", "")
            metadata = {k: v for k, v in result.payload.items() if k != "image_uri"}
            
            # Extract gcs_url from metadata and convert to public HTTP URL
            gcs_url = metadata.get("gcs_url", "")
            image_url = ""
            
            if gcs_url:
                # Convert gs:// URL to public HTTP URL
                if gcs_url.startswith("gs://"):
                    path = gcs_url[5:]  # Remove "gs://" prefix
                    image_url = f"https://storage.googleapis.com/{path}"
                    logger.debug(f"✅ Converted gs:// to public URL for {image_uri[:50]}: {image_url[:80]}")
                elif gcs_url.startswith("https://") or gcs_url.startswith("http://"):
                    # Already an HTTP URL
                    image_url = gcs_url
                    logger.debug(f"✅ Using existing HTTP URL for {image_uri[:50]}: {image_url[:80]}")
                elif gcs_url.startswith("file://"):
                    # File URL - pass through so proxy endpoint can serve it
                    image_url = gcs_url
                    logger.debug(f"✅ Found file:// URL for {image_uri[:50]}: {image_url[:80]} (will use proxy)")
                else:
                    # Unknown format - log warning
                    logger.warning(f"⚠️  Unknown gcs_url format for {image_uri[:50]}: {gcs_url[:80]}")
                    image_url = image_uri  # Fallback
            elif metadata.get("public_url"):
                # Use public_url directly if available (stored during ingestion)
                image_url = metadata["public_url"]
                logger.debug(f"✅ Found public_url in metadata for {image_uri[:50]}: {image_url[:80]}")
            else:
                # No gcs_url or public_url in metadata - log warning
                logger.warning(f"⚠️  No gcs_url or public_url in metadata for {image_uri[:50]}, metadata keys: {list(metadata.keys())}")
                image_url = image_uri  # Will be handled by API endpoint KG fallback
            
            formatted_results.append({
                "image_uri": image_uri,
                "image_url": image_url,  # Add accessible URL field (may be placeholder if no gcs_url)
                "score": result.score,
                "metadata": metadata,
            })
        
        logger.info(f"Found {len(formatted_results)} similar images")
        return formatted_results
    
    def get_embedding(self, image_uri: str) -> Optional[List[float]]:
        """
        Retrieve a stored embedding by image URI.
        
        Args:
            image_uri: The URI of the image in the knowledge graph
        
        Returns:
            The embedding vector if found, None otherwise
        """
        if not image_uri:
            logger.warning("get_embedding called without image_uri")
            return None

        preferred_id = generate_stable_point_id(image_uri)
        legacy_id = generate_legacy_point_id(image_uri)
        # Always prefer the deterministic ID but also query the legacy ID so we
        # can read points that were stored before this fix shipped.
        query_ids = [preferred_id]
        if str(legacy_id) != preferred_id:
            query_ids.append(legacy_id)
        
        try:
            result = self.qdrant_client.retrieve(
                collection_name=self.collection_name,
                ids=query_ids,
                with_vectors=True,
            )
            
            if not result:
                return None

            # Look for deterministic ID first
            for record in result:
                if str(record.id) == preferred_id:
                    return record.vector

            # Fallback to legacy ID
            for record in result:
                if str(record.id) == str(legacy_id):
                    logger.info(
                        f"Using legacy Qdrant point ID for {image_uri[:50]} – "
                        "consider re-ingesting to upgrade to sha256 IDs"
                    )
                    return record.vector

            # If Qdrant returned something unexpected, just return first vector
            return result[0].vector
            
        except Exception as e:
            logger.warning(f"Failed to retrieve embedding for {image_uri}: {e}")
        
        return None
    
    async def cluster_images_by_similarity(
        self,
        image_uris: List[str],
        min_similarity: float = 0.7,
        min_cluster_size: int = 2,
        kg_manager: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Cluster images by embedding similarity using DBSCAN algorithm.
        
        Groups similar images together based on their embeddings. Images with similarity
        >= min_similarity are grouped into clusters. Stores cluster assignments in KG
        if kg_manager is provided.
        
        Args:
            image_uris: List of image URIs to cluster
            min_similarity: Minimum cosine similarity for images to be in same cluster (0.0-1.0)
            min_cluster_size: Minimum number of images required to form a cluster
            kg_manager: Optional KnowledgeGraphManager to store cluster assignments in KG
        
        Returns:
            Dictionary with:
            - clusters: List of clusters, each containing list of image URIs
            - noise: List of image URIs that don't belong to any cluster
            - cluster_uris: List of cluster URIs created in KG (if kg_manager provided)
        
        Raises:
            ImportError: If scikit-learn is not available
            ValueError: If image_uris is empty or embeddings not found
        """
        if not CLUSTERING_AVAILABLE:
            raise ImportError(
                "Clustering requires scikit-learn. Install with: pip install scikit-learn"
            )
        
        if not image_uris:
            raise ValueError("image_uris cannot be empty")
        
        logger.info(f"Clustering {len(image_uris)} images with min_similarity={min_similarity}")
        
        # Retrieve embeddings for all images
        embeddings = []
        valid_uris = []
        for uri in image_uris:
            embedding = self.get_embedding(uri)
            if embedding:
                embeddings.append(embedding)
                valid_uris.append(uri)
            else:
                logger.warning(f"No embedding found for {uri[:50]}, skipping")
        
        if len(embeddings) < min_cluster_size:
            logger.warning(
                f"Not enough images with embeddings ({len(embeddings)} < {min_cluster_size})"
            )
            return {
                "clusters": [],
                "noise": valid_uris,
                "cluster_uris": [],
            }
        
        # Convert to numpy array for DBSCAN
        embedding_matrix = np.array(embeddings, dtype=np.float32)
        
        # DBSCAN uses distance, not similarity
        # Convert similarity threshold to distance: distance = 1 - similarity
        # For cosine similarity in [0, 1], distance in [0, 1]
        max_distance = 1.0 - min_similarity
        
        # Run DBSCAN clustering
        # eps: maximum distance between samples in same cluster
        # min_samples: minimum number of samples in a cluster
        clusterer = DBSCAN(eps=max_distance, min_samples=min_cluster_size, metric='cosine')
        cluster_labels = clusterer.fit_predict(embedding_matrix)
        
        # Organize results
        clusters = {}
        noise = []
        
        for idx, label in enumerate(cluster_labels):
            uri = valid_uris[idx]
            if label == -1:  # -1 indicates noise (outlier)
                noise.append(uri)
            else:
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(uri)
        
        cluster_list = list(clusters.values())
        cluster_uris = []
        
        # Store cluster assignments in KG if manager provided
        if kg_manager:
            from rdflib import URIRef, Literal, RDF
            from rdflib.namespace import Namespace
            
            KG = Namespace("http://example.org/kg#")
            CLUSTER = Namespace("http://example.org/cluster#")
            
            for cluster_idx, image_uris_in_cluster in enumerate(cluster_list):
                cluster_id = f"cluster_{uuid.uuid4().hex[:8]}"
                cluster_uri = f"http://example.org/cluster/{cluster_id}"
                cluster_ref = URIRef(cluster_uri)
                
                # Create cluster node
                try:
                    await kg_manager.add_triple(
                        str(cluster_ref),
                        str(RDF.type),
                        str(CLUSTER.ImageCluster)
                    )
                    await kg_manager.add_triple(
                        str(cluster_ref),
                        str(KG.clusterSize),
                        str(len(image_uris_in_cluster))
                    )
                    await kg_manager.add_triple(
                        str(cluster_ref),
                        str(KG.minSimilarity),
                        str(min_similarity)
                    )
                    
                    # Link each image to cluster
                    for image_uri in image_uris_in_cluster:
                        await kg_manager.add_triple(
                            image_uri,
                            str(KG.belongsToCluster),
                            str(cluster_ref)
                        )
                        await kg_manager.add_triple(
                            str(cluster_ref),
                            str(KG.hasMember),
                            image_uri
                        )
                    
                    cluster_uris.append(cluster_uri)
                    logger.debug(f"Created cluster {cluster_id} with {len(image_uris_in_cluster)} images")
                except Exception as e:
                    logger.error(f"Failed to store cluster {cluster_id} in KG: {e}")
                    # Continue with other clusters
        
        logger.info(
            f"Clustering complete: {len(cluster_list)} clusters, {len(noise)} noise points"
        )
        
        return {
            "clusters": cluster_list,
            "noise": noise,
            "cluster_uris": cluster_uris,
        }


def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Compute cosine similarity between two embedding vectors.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Cosine similarity score between -1.0 and 1.0
        (1.0 = identical, 0.0 = orthogonal, -1.0 = opposite)
        
    Raises:
        ValueError: If embeddings are empty or different lengths
        
    Example:
        >>> emb1 = [1.0, 0.0, 0.0]
        >>> emb2 = [1.0, 0.0, 0.0]
        >>> compute_similarity(emb1, emb2)
        1.0
    """
    if not embedding1 or not embedding2:
        raise ValueError("Embeddings cannot be empty")
    
    if len(embedding1) != len(embedding2):
        raise ValueError(
            f"Embeddings must have same length: {len(embedding1)} != {len(embedding2)}"
        )
    
    # Compute dot product
    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
    
    # Compute magnitudes
    magnitude1 = sum(a * a for a in embedding1) ** 0.5
    magnitude2 = sum(b * b for b in embedding2) ** 0.5
    
    # Avoid division by zero
    if magnitude1 == 0.0 or magnitude2 == 0.0:
        return 0.0
    
    # Compute cosine similarity
    cosine_sim = dot_product / (magnitude1 * magnitude2)
    
    # Clamp to [-1.0, 1.0] to handle floating point errors
    return max(-1.0, min(1.0, cosine_sim))


# Convenience function for standalone use
async def embed_image_file(image_path: Path) -> Tuple[List[float], str]:
    """
    Convenience function to embed a single image file.
    
    Args:
        image_path: Path to image file
    
    Returns:
        Tuple of (embedding_vector, description)
    """
    service = ImageEmbeddingService()
    return await service.embed_image(image_path)

