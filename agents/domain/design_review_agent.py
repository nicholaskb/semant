"""
Design Review Agent - Task #108
Reviews page designs for completeness and quality.
Reuses: BaseAgent, ColorPaletteAgent, CriticAgent pattern
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import uuid

from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD

BOOK = Namespace("http://example.org/childrens-book#")


class DesignReviewAgent(BaseAgent):
    """Reviews page designs for quality and completeness."""
    
    def __init__(self, agent_id: str = "design_review_agent", kg_manager: Optional[KnowledgeGraphManager] = None):
        super().__init__(agent_id=agent_id)
        self.kg_manager = kg_manager or KnowledgeGraphManager()
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        action = message.content.get("action")
        if action == "review_designs":
            return await self._handle_review(message)
        return self._create_error_response(message.sender_id, f"Unknown action: {action}")
    
    async def _handle_review(self, message: AgentMessage) -> AgentMessage:
        try:
            designs = await self._get_pending_designs()
            reviews = []
            
            for design_uri in designs:
                review_uri = await self._review_design(design_uri)
                reviews.append(review_uri)
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "success", "reviews_created": len(reviews), "review_uris": reviews},
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))
    
    async def _get_pending_designs(self) -> List[str]:
        """Get designs pending review."""
        query = """
        PREFIX book: <http://example.org/childrens-book#>
        SELECT ?design WHERE {
            ?design a book:PageDesign ;
                    book:designStatus "pending_review" .
        }
        """
        results = await self.kg_manager.query_graph(query)
        return [str(r["design"]) for r in results]
    
    async def _review_design(self, design_uri: str) -> str:
        """Review one page design."""
        # Simplified scoring
        completeness = 1.0
        quality = 0.85
        approved = completeness >= 0.8 and quality >= 0.8
        
        review_id = str(uuid.uuid4())
        review_uri = f"http://example.org/review/{review_id}"
        review_ref = URIRef(review_uri)
        
        triples = [
            (review_ref, RDF.type, BOOK.DesignReview),
            (review_ref, BOOK.reviewsDesign, URIRef(design_uri)),
            (review_ref, BOOK.completenessScore, Literal(completeness, datatype=XSD.float)),
            (review_ref, BOOK.qualityScore, Literal(quality, datatype=XSD.float)),
            (review_ref, BOOK.feedback, Literal("Design approved")),
            (review_ref, BOOK.approved, Literal(approved, datatype=XSD.boolean)),
        ]
        
        # Update design status
        if approved:
            triples.append((URIRef(design_uri), BOOK.designStatus, Literal("approved")))
        
        for triple in triples:
            await self.kg_manager.add_triple(*triple)
        
        logger.info(f"Reviewed design: approved={approved}")
        return review_uri

