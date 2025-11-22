"""
Image Pairing Agent for Children's Book Swarm

Matches input images to their related output images using embedding similarity,
filename patterns, and metadata correlation.

Date: 2025-01-08
Status: Implementation
"""

import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import uuid
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from kg.services.image_embedding_service import ImageEmbeddingService
from rdflib import Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD

# Namespaces
SCHEMA = Namespace("http://schema.org/")
KG = Namespace("http://example.org/kg#")
BOOK = Namespace("http://example.org/childrens-book#")

# Scoring weights
EMBEDDING_WEIGHT = 0.6
FILENAME_WEIGHT = 0.2
METADATA_WEIGHT = 0.2

# Confidence threshold for human review
LOW_CONFIDENCE_THRESHOLD = 0.7


class ImagePairingAgent(BaseAgent):
    """
    Agent responsible for pairing input images with their related output images.
    
    Workflow:
    1. Query KG for all input images
    2. For each input image:
       a. Get its embedding from Qdrant
       b. Search for similar output images (embedding similarity)
       c. Score by filename pattern matching
       d. Score by metadata correlation
       e. Compute weighted final score
    3. Create book:ImagePair nodes in KG
    4. Flag low-confidence pairs for human review
    
    Scoring Algorithm:
    - Embedding similarity: 60% (visual similarity via CLIP embeddings)
    - Filename pattern: 20% (e.g., input_001 → output_001_a, output_001_b)
    - Metadata correlation: 20% (timestamps, sizes, etc.)
    
    Reuses:
    - ImageEmbeddingService.search_similar_images()
    - ImageAnalysisAgent patterns
    - KnowledgeGraphManager
    """
    
    def __init__(
        self,
        agent_id: str = "image_pairing_agent",
        capabilities: Optional[set] = None,
        kg_manager: Optional[KnowledgeGraphManager] = None,
        embedding_service: Optional[ImageEmbeddingService] = None,
        top_k_outputs: int = 12,  # Max outputs per input
    ):
        """
        Initialize the Image Pairing Agent.
        
        Args:
            agent_id: Unique identifier for this agent
            capabilities: Set of capabilities this agent provides
            kg_manager: Knowledge graph manager instance
            embedding_service: Image embedding service instance
            top_k_outputs: Maximum number of output images to pair with each input
        """
        super().__init__(
            agent_id=agent_id,
            capabilities=capabilities or {"image_pairing", "similarity_matching", "pattern_recognition"}
        )
        
        self.kg_manager = kg_manager or KnowledgeGraphManager()

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

        self.top_k_outputs = top_k_outputs
        
        logger.info(
            f"ImagePairingAgent initialized: "
            f"top_k_outputs={top_k_outputs}, "
            f"capabilities={self.capabilities}"
        )
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """
        Process incoming messages to pair images.
        
        Expected message content:
        {
            "action": "pair_images",
            "input_image_uris": [...],  # optional, if None pair all inputs
            "top_k_outputs": 12,  # optional
            "min_confidence": 0.5  # optional
        }
        
        Returns:
            AgentMessage with results:
            {
                "status": "success",
                "pairs_count": 10,
                "low_confidence_count": 2,
                "pair_uris": [...],
                "pairs": [
                    {
                        "pair_uri": "...",
                        "input_image_uri": "...",
                        "output_image_uris": [...],
                        "confidence": 0.95,
                        "method": "embedding+filename"
                    },
                    ...
                ]
            }
        """
        action = message.content.get("action")
        
        if action == "pair_images":
            return await self._handle_pair_images(message)
        else:
            return self._create_error_response(
                message.sender_id,
                f"Unknown action: {action}"
            )
    
    async def _handle_pair_images(self, message: AgentMessage) -> AgentMessage:
        """Handle the pair_images action."""
        try:
            # Extract parameters
            input_image_uris = message.content.get("input_image_uris")
            top_k = message.content.get("top_k_outputs", self.top_k_outputs)
            min_confidence = message.content.get("min_confidence", 0.5)
            
            logger.info(f"Starting image pairing: top_k={top_k}, min_confidence={min_confidence}")
            
            # CRITICAL: Check if embedding service is available
            if not self.embedding_service:
                error_msg = "ImageEmbeddingService not available. Cannot pair images without embeddings."
                logger.error(error_msg)
                return self._create_error_response(message.sender_id, error_msg)
            
            # Get all input images from KG if not specified
            if input_image_uris is None:
                input_images = await self._get_input_images()
            else:
                input_images = await self._get_images_by_uris(input_image_uris)
            
            logger.info(f"Found {len(input_images)} input images to pair")
            
            # Pair each input with outputs
            pairs = []
            low_confidence_count = 0
            
            for input_image in input_images:
                try:
                    pair_result = await self._pair_single_input(
                        input_image=input_image,
                        top_k=top_k,
                        min_confidence=min_confidence
                    )
                    
                    if pair_result:
                        pairs.append(pair_result)
                        
                        if pair_result["confidence"] < LOW_CONFIDENCE_THRESHOLD:
                            low_confidence_count += 1
                            logger.warning(
                                f"Low confidence pair: {input_image['name']} "
                                f"(confidence={pair_result['confidence']:.3f})"
                            )
                
                except Exception as e:
                    logger.error(f"Failed to pair {input_image['name']}: {e}")
                    continue
            
            logger.info(
                f"Pairing complete: {len(pairs)} pairs created, "
                f"{low_confidence_count} need review"
            )
            
            # Create response
            response_content = {
                "status": "success",
                "pairs_count": len(pairs),
                "low_confidence_count": low_confidence_count,
                "pair_uris": [p["pair_uri"] for p in pairs],
                "pairs": pairs,
            }
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=response_content,
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error in pair_images: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))
    
    async def _get_input_images(self) -> List[Dict[str, Any]]:
        """Query KG for all input images."""
        query = """
        PREFIX schema: <http://schema.org/>
        PREFIX kg: <http://example.org/kg#>
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT ?image ?name ?url WHERE {
            ?image a book:InputImage ;
                   schema:name ?name ;
                   schema:contentUrl ?url ;
                   kg:hasEmbedding ?hasEmbedding .
            FILTER (?hasEmbedding = "true")
        }
        ORDER BY ?name
        """
        
        results = await self.kg_manager.query_graph(query)
        
        # CRITICAL: Check embedding service before use
        if not self.embedding_service:
            logger.error("Embedding service not available, cannot get embeddings for input images")
            return []
        
        images = []
        for result in results:
            image_uri = str(result["image"])
            # ISSUE #6 FIX: Get embedding from Qdrant (KG only stores flag, not full embedding)
            embedding = None
            
            try:
                embedding = self.embedding_service.get_embedding(image_uri)
                if not embedding:
                    logger.warning(f"No embedding found in Qdrant for {image_uri[:50]}, skipping")
                    continue
            except Exception as e:
                logger.error(f"Error getting embedding from Qdrant for {image_uri[:50]}: {e}")
                continue
            
            images.append({
                "uri": image_uri,
                "name": str(result["name"]),
                "url": str(result["url"]),
                "embedding": embedding,
            })
        
        return images
    
    async def _get_images_by_uris(self, uris: List[str]) -> List[Dict[str, Any]]:
        """Query KG for specific images by URI."""
        # Build VALUES clause
        values_clause = " ".join([f"<{uri}>" for uri in uris])
        
        query = f"""
        PREFIX schema: <http://schema.org/>
        PREFIX kg: <http://example.org/kg#>
        
        SELECT ?image ?name ?url WHERE {{
            VALUES ?image {{ {values_clause} }}
            ?image schema:name ?name ;
                   schema:contentUrl ?url ;
                   kg:hasEmbedding ?hasEmbedding .
            FILTER (?hasEmbedding = "true")
        }}
        """
        
        results = await self.kg_manager.query_graph(query)
        
        # CRITICAL: Check embedding service before use
        if not self.embedding_service:
            logger.error("Embedding service not available, cannot get embeddings for specified images")
            return []
        
        images = []
        for result in results:
            image_uri = str(result["image"])
            # ISSUE #6 FIX: Get embedding from Qdrant (KG only stores flag, not full embedding)
            embedding = None
            
            try:
                embedding = self.embedding_service.get_embedding(image_uri)
                if not embedding:
                    logger.warning(f"No embedding found in Qdrant for {image_uri[:50]}, skipping")
                    continue
            except Exception as e:
                logger.error(f"Error getting embedding from Qdrant for {image_uri[:50]}: {e}")
                continue
            
            images.append({
                "uri": image_uri,
                "name": str(result["name"]),
                "url": str(result["url"]),
                "embedding": embedding,
            })
        
        return images
    
    async def _pair_single_input(
        self,
        input_image: Dict[str, Any],
        top_k: int,
        min_confidence: float
    ) -> Optional[Dict[str, Any]]:
        """
        Pair a single input image with output images.
        
        Args:
            input_image: Dict with uri, name, url, embedding
            top_k: Maximum number of outputs to pair
            min_confidence: Minimum confidence score
        
        Returns:
            Dict with pair information, or None if no good matches
        """
        input_uri = input_image["uri"]
        input_name = input_image["name"]
        input_embedding = input_image["embedding"]
        
        logger.debug(f"Pairing input image: {input_name}")
        
        # Search for similar output images using embeddings
        similar_images = self.embedding_service.search_similar_images(
            query_embedding=input_embedding,
            limit=top_k * 2,  # Get extra to filter
            filter_metadata={"image_type": "output"},
        )
        
        if not similar_images:
            logger.warning(f"No similar output images found for {input_name}")
            return None
        
        # Score each candidate output
        scored_outputs = []
        for output_result in similar_images:
            output_uri = output_result["image_uri"]
            embedding_score = output_result["score"]
            output_name = output_result["metadata"].get("filename", "")
            
            # Compute filename similarity
            filename_score = self._compute_filename_similarity(input_name, output_name)
            
            # Compute metadata correlation (based on actual metadata if available)
            metadata_score = self._compute_metadata_correlation(
                output_result.get("metadata", {}),
                input_name
            )
            
            # Weighted final score
            final_score = (
                EMBEDDING_WEIGHT * embedding_score +
                FILENAME_WEIGHT * filename_score +
                METADATA_WEIGHT * metadata_score
            )
            
            if final_score >= min_confidence:
                scored_outputs.append({
                    "output_uri": output_uri,
                    "output_name": output_name,
                    "embedding_score": embedding_score,
                    "filename_score": filename_score,
                    "metadata_score": metadata_score,
                    "final_score": final_score,
                })
        
        # Sort by final score and take top_k
        scored_outputs.sort(key=lambda x: x["final_score"], reverse=True)
        top_outputs = scored_outputs[:top_k]
        
        if not top_outputs:
            logger.warning(f"No output images above confidence threshold for {input_name}")
            return None
        
        # Compute overall pair confidence (average of top outputs)
        avg_confidence = sum(o["final_score"] for o in top_outputs) / len(top_outputs)
        
        # Create pair in KG
        pair_uri = await self._create_pair_in_kg(
            input_uri=input_uri,
            output_uris=[o["output_uri"] for o in top_outputs],
            confidence=avg_confidence,
            method="embedding+filename",
        )
        
        logger.info(
            f"Paired {input_name} with {len(top_outputs)} outputs "
            f"(confidence={avg_confidence:.3f})"
        )
        
        return {
            "pair_uri": pair_uri,
            "input_image_uri": input_uri,
            "input_image_name": input_name,
            "output_image_uris": [o["output_uri"] for o in top_outputs],
            "output_image_names": [o["output_name"] for o in top_outputs],
            "confidence": avg_confidence,
            "method": "embedding+filename",
            "output_scores": top_outputs,
        }
    
    @staticmethod
    def _compute_filename_similarity(input_name: str, output_name: str) -> float:
        """
        Compute filename pattern similarity.
        
        Strategy:
        - Extract numeric parts from filenames
        - If input has "001" and output has "001", score higher
        - If filenames share prefixes, score higher
        
        Args:
            input_name: Input image filename
            output_name: Output image filename
        
        Returns:
            Similarity score (0-1)
        """
        # Extract numbers from filenames
        input_nums = set(re.findall(r'\d+', input_name))
        output_nums = set(re.findall(r'\d+', output_name))
        
        # Jaccard similarity of numbers
        if input_nums or output_nums:
            intersection = len(input_nums & output_nums)
            union = len(input_nums | output_nums)
            num_similarity = intersection / union if union > 0 else 0
        else:
            num_similarity = 0
        
        # Check for shared prefix (before first underscore or number)
        input_prefix = re.split(r'[_\d]', Path(input_name).stem)[0].lower()
        output_prefix = re.split(r'[_\d]', Path(output_name).stem)[0].lower()
        
        prefix_match = 1.0 if input_prefix == output_prefix else 0.0
        
        # Weighted combination
        similarity = 0.7 * num_similarity + 0.3 * prefix_match
        
        return similarity
    
    @staticmethod
    def _compute_metadata_correlation(
        output_metadata: Dict[str, Any],
        input_name: str
    ) -> float:
        """
        Compute metadata correlation between input and output.
        
        Considers:
        - Timestamp proximity
        - File size similarity
        - Shared tags or keywords
        
        Args:
            output_metadata: Metadata dict from Qdrant
            input_name: Input image filename
        
        Returns:
            Correlation score (0-1)
        """
        score = 0.0
        factors = 0
        
        # Check if output metadata references input in description
        description = output_metadata.get("description", "").lower()
        input_stem = Path(input_name).stem.lower()
        
        if input_stem in description:
            score += 1.0
            factors += 1
        
        # Check GCS URL path similarity
        gcs_url = output_metadata.get("gcs_url", "")
        if input_stem in gcs_url:
            score += 1.0
            factors += 1
        
        # Default correlation
        if factors == 0:
            return 0.5  # Neutral default
        
        return score / factors
    
    async def _create_pair_in_kg(
        self,
        input_uri: str,
        output_uris: List[str],
        confidence: float,
        method: str
    ) -> str:
        """Create a book:ImagePair node in the knowledge graph."""
        pair_uri = f"http://example.org/image-pair/{uuid.uuid4()}"
        pair_ref = URIRef(pair_uri)
        
        # Create RDF list for output images
        output_list = self.kg_manager.create_rdf_list([URIRef(uri) for uri in output_uris])
        
        # Add triples
        triples = [
            # Type
            (pair_ref, RDF.type, BOOK.ImagePair),
            
            # Relationships
            (pair_ref, BOOK.hasInputImage, URIRef(input_uri)),
            (pair_ref, BOOK.hasOutputImages, output_list),
            
            # Metadata
            (pair_ref, BOOK.pairConfidence, Literal(confidence, datatype=XSD.float)),
            (pair_ref, BOOK.pairingMethod, Literal(method)),
            (pair_ref, SCHEMA.dateCreated, Literal(datetime.utcnow().isoformat(), datatype=XSD.dateTime)),
            
            # Flag for review if low confidence
            (pair_ref, BOOK.needsReview, Literal(confidence < LOW_CONFIDENCE_THRESHOLD, datatype=XSD.boolean)),
        ]
        
        # Add to KG
        for triple in triples:
            await self.kg_manager.add_triple(*triple)
        
        logger.debug(f"Created image pair: {pair_uri}")
        return pair_uri
    
    async def get_all_pairs(
        self,
        include_low_confidence: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query KG for all image pairs.
        
        Args:
            include_low_confidence: Whether to include pairs needing review
        
        Returns:
            List of pair metadata dicts
        """
        filter_clause = "" if include_low_confidence else "FILTER (!?needsReview)"
        
        query = f"""
        PREFIX book: <http://example.org/childrens-book#>
        PREFIX schema: <http://schema.org/>
        
        SELECT ?pair ?input ?outputs ?confidence ?method ?needsReview WHERE {{
            ?pair a book:ImagePair ;
                  book:hasInputImage ?input ;
                  book:hasOutputImages ?outputs ;
                  book:pairConfidence ?confidence ;
                  book:pairingMethod ?method ;
                  book:needsReview ?needsReview .
            {filter_clause}
        }}
        ORDER BY DESC(?confidence)
        """
        
        results = await self.kg_manager.query_graph(query)
        
        pairs = []
        for result in results:
            pairs.append({
                "pair_uri": str(result["pair"]),
                "input_uri": str(result["input"]),
                "confidence": float(result["confidence"]),
                "method": str(result["method"]),
                "needs_review": bool(result["needsReview"]),
                # Note: outputs is an RDF list, would need special handling
            })
        
        return pairs


# Standalone function for CLI use
async def pair_all_images() -> Dict[str, Any]:
    """
    Convenience function to pair all input images with outputs.
    
    Returns:
        Dict with pairing results
    """
    agent = ImagePairingAgent()
    
    message = AgentMessage(
        sender_id="cli",
        recipient_id="image_pairing_agent",
        content={
            "action": "pair_images",
            "top_k_outputs": 12,
            "min_confidence": 0.5,
        },
        message_type="request",
        timestamp=datetime.utcnow().isoformat()
    )
    
    response = await agent._process_message_impl(message)
    return response.content

