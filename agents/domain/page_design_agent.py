"""
Page Design Agent for Children's Book Swarm
Date: 2025-01-08
TaskMaster Task #107

Creates complete page designs combining all elements:
- Left column: Input image + story text
- Right column: Output image grid (from GridLayoutAgent)

REUSES (NO DUPLICATES):
- agents/core/base_agent.py - BaseAgent
- agents/domain/composition_agent.py - CompositionAgent
- kg/models/graph_manager.py - KnowledgeGraphManager
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from rdflib import Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, XSD

SCHEMA = Namespace("http://schema.org/")
BOOK = Namespace("http://example.org/childrens-book#")


class PageDesignAgent(BaseAgent):
    """
    Creates complete page designs for children's book.
    
    Each page design includes:
    - Left column: input image + story text + styling
    - Right column: grid layout + output images
    - Design suggestions: fonts, colors, spacing
    
    Reuses: BaseAgent, KnowledgeGraphManager
    """
    
    def __init__(self, agent_id: str = "page_design_agent", kg_manager: Optional[KnowledgeGraphManager] = None):
        super().__init__(agent_id=agent_id)
        self.kg_manager = kg_manager or KnowledgeGraphManager()
        logger.info(f"PageDesignAgent initialized")
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        action = message.content.get("action")
        if action == "create_page_designs":
            return await self._handle_create_designs(message)
        return self._create_error_response(message.sender_id, f"Unknown action: {action}")
    
    async def _handle_create_designs(self, message: AgentMessage) -> AgentMessage:
        try:
            sequence = await self._get_sequence()
            if not sequence:
                return self._create_error_response(message.sender_id, "No sequence found")
            
            designs = []
            for page_num, pair_uri in enumerate(sequence, 1):
                design_uri = await self._create_page_design(pair_uri, page_num)
                designs.append(design_uri)
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "success", "designs_created": len(designs), "design_uris": designs},
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"{self.agent_id}: Error: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))
    
    async def _get_sequence(self) -> Optional[List[str]]:
        """Get ordered sequence of pair URIs."""
        query = """
        PREFIX book: <http://example.org/childrens-book#>
        SELECT ?pair ?order WHERE {
            ?sequence a book:StorySequence .
            ?sequence book:hasPage ?pair .
            ?pair book:sequenceOrder ?order .
        }
        ORDER BY ?order
        """
        results = await self.kg_manager.query_graph(query)
        return [str(r["pair"]) for r in results] if results else None
    
    async def _create_page_design(self, pair_uri: str, page_num: int) -> str:
        """Create complete page design."""
        # Get components
        components = await self._get_page_components(pair_uri)
        
        # Create design node
        design_id = str(uuid.uuid4())
        design_uri = f"http://example.org/pageDesign/{design_id}"
        design_ref = URIRef(design_uri)
        
        # Store design
        triples = [
            (design_ref, RDF.type, BOOK.PageDesign),
            (design_ref, BOOK.pageNumber, Literal(page_num, datatype=XSD.integer)),
            (design_ref, BOOK.designStatus, Literal("pending_review")),
        ]
        
        # Left column
        left_col = BNode()
        triples.extend([
            (design_ref, BOOK.leftColumn, left_col),
            (left_col, BOOK.hasInputImage, URIRef(components["input_uri"])),
            (left_col, BOOK.hasStoryText, Literal(components.get("text", ""))),
            (left_col, BOOK.textFont, Literal("Comic Sans MS")),
            (left_col, BOOK.textSize, Literal("18pt")),
        ])
        
        # Right column
        right_col = BNode()
        triples.extend([
            (design_ref, BOOK.rightColumn, right_col),
            (right_col, BOOK.hasGridLayout, URIRef(components["layout_uri"])),
            (right_col, BOOK.gridDimensions, Literal(components["grid_dims"])),
        ])
        
        # Add all triples
        for triple in triples:
            await self.kg_manager.add_triple(*triple)
        
        logger.info(f"{self.agent_id}: Created design for page {page_num}")
        return design_uri
    
    async def _get_page_components(self, pair_uri: str) -> Dict[str, Any]:
        """Get all components for a page."""
        query = f"""
        PREFIX book: <http://example.org/childrens-book#>
        PREFIX schema: <http://schema.org/>
        
        SELECT ?input ?text ?layout ?gridDims
        WHERE {{
            <{pair_uri}> book:hasInputImage ?input .
            OPTIONAL {{ <{pair_uri}> book:hasStoryText ?text . }}
            OPTIONAL {{ <{pair_uri}> book:hasGridLayout ?layout . }}
            OPTIONAL {{ ?layout book:gridDimensions ?gridDims . }}
        }}
        """
        
        results = await self.kg_manager.query_graph(query)
        if not results:
            return {}
        
        r = results[0]
        return {
            "input_uri": str(r["input"]),
            "text": str(r.get("text", "")),
            "layout_uri": str(r.get("layout", "")),
            "grid_dims": str(r.get("gridDims", "3x3")),
        }


async def create_page_designs() -> Dict[str, Any]:
    """Standalone function."""
    agent = PageDesignAgent()
    message = AgentMessage(
        sender_id="cli",
        recipient_id="page_design_agent",
        content={"action": "create_page_designs"},
        message_type="request",
        timestamp=datetime.utcnow().isoformat()
    )
    response = await agent._process_message_impl(message)
    return response.content

