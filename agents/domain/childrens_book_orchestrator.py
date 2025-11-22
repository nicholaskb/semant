"""
Children's Book Orchestrator - Task #110
Main coordinator for the entire book generation workflow.
Reuses: OrchestrationWorkflow pattern, all 9 specialist agents
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
import uuid

from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager

# ✅ REUSE: All specialist agents
from agents.domain.image_ingestion_agent import ImageIngestionAgent
from agents.domain.image_pairing_agent import ImagePairingAgent
from agents.domain.story_sequencing_agent import StorySequencingAgent
from agents.domain.spatial_color_agent import SpatialColorAgent
from agents.domain.grid_layout_agent import GridLayoutAgent
from agents.domain.story_writer_agent import StoryWriterAgent
from agents.domain.page_design_agent import PageDesignAgent
from agents.domain.design_review_agent import DesignReviewAgent
from agents.domain.book_layout_agent import BookLayoutAgent

from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF

BOOK = Namespace("http://example.org/childrens-book#")
PROV = Namespace("http://www.w3.org/ns/prov#")


class ChildrensBookOrchestrator(BaseAgent):
    """
    Master orchestrator for children's book generation.
    
    9-Step Workflow:
    1. Download & Ingest (ImageIngestionAgent)
    2. Pair Images (ImagePairingAgent)
    3. Sequence Story (StorySequencingAgent)
    4. Arrange Colors (SpatialColorAgent)
    5. Decide Grids (GridLayoutAgent)
    6. Write Story (StoryWriterAgent)
    7. Design Pages (PageDesignAgent)
    8. Review Designs (DesignReviewAgent)
    9. Generate Book (BookLayoutAgent)
    
    Reuses: OrchestrationWorkflow pattern from agents/domain/orchestration_workflow.py
    """
    
    def __init__(self, agent_id: str = "childrens_book_orchestrator", kg_manager: Optional[KnowledgeGraphManager] = None):
        super().__init__(agent_id=agent_id)
        self.kg_manager = kg_manager or KnowledgeGraphManager()
        
        # Initialize all specialist agents
        self.ingestion_agent = ImageIngestionAgent(kg_manager=self.kg_manager)
        self.pairing_agent = ImagePairingAgent(kg_manager=self.kg_manager)
        self.sequencing_agent = StorySequencingAgent(kg_manager=self.kg_manager)
        self.color_agent = SpatialColorAgent(kg_manager=self.kg_manager)
        self.grid_agent = GridLayoutAgent(kg_manager=self.kg_manager)
        self.writer_agent = StoryWriterAgent(kg_manager=self.kg_manager)
        self.design_agent = PageDesignAgent(kg_manager=self.kg_manager)
        self.review_agent = DesignReviewAgent(kg_manager=self.kg_manager)
        self.layout_agent = BookLayoutAgent(kg_manager=self.kg_manager)
        
        logger.info("ChildrensBookOrchestrator initialized with 9 specialist agents")
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        action = message.content.get("action")
        if action == "generate_book":
            return await self._handle_generate_book(message)
        return self._create_error_response(message.sender_id, f"Unknown action: {action}")
    
    async def _handle_generate_book(self, message: AgentMessage) -> AgentMessage:
        """Execute complete book generation workflow."""
        try:
            workflow_id = str(uuid.uuid4())
            start_time = datetime.utcnow()
            
            logger.info(f"Starting book generation workflow: {workflow_id}")
            
            # Extract params
            bucket = message.content.get("bucket")
            input_prefix = message.content.get("input_prefix", "input_kids_monster/")
            output_prefix = message.content.get("output_prefix", "generated_images/")
            
            # Step 1: Ingest images
            logger.info("Step 1/9: Image ingestion")
            ingest_msg = AgentMessage(
                sender_id=self.agent_id,
                recipient_id="image_ingestion_agent",
                content={"action": "ingest_images", "input_prefix": input_prefix, "output_prefix": output_prefix},
                message_type="request"
            )
            ingest_result = await self.ingestion_agent._process_message_impl(ingest_msg)
            
            # Step 2: Pair images
            logger.info("Step 2/9: Image pairing")
            pair_msg = AgentMessage(
                sender_id=self.agent_id,
                recipient_id="image_pairing_agent",
                content={"action": "pair_images"},
                message_type="request"
            )
            pair_result = await self.pairing_agent._process_message_impl(pair_msg)
            
            # Step 3: Sequence story
            logger.info("Step 3/9: Story sequencing")
            seq_msg = AgentMessage(
                sender_id=self.agent_id,
                recipient_id="story_sequencing_agent",
                content={"action": "sequence_story"},
                message_type="request"
            )
            seq_result = await self.sequencing_agent._process_message_impl(seq_msg)
            
            # Step 4: Arrange by color
            logger.info("Step 4/9: Spatial color arrangement")
            color_msg = AgentMessage(
                sender_id=self.agent_id,
                recipient_id="spatial_color_agent",
                content={"action": "arrange_by_color"},
                message_type="request"
            )
            color_result = await self.color_agent._process_message_impl(color_msg)
            
            # Step 5: Create grids
            logger.info("Step 5/9: Grid layout creation")
            grid_msg = AgentMessage(
                sender_id=self.agent_id,
                recipient_id="grid_layout_agent",
                content={"action": "create_grid_layouts"},
                message_type="request"
            )
            grid_result = await self.grid_agent._process_message_impl(grid_msg)
            
            # Step 6: Write story
            logger.info("Step 6/9: Story writing")
            write_msg = AgentMessage(
                sender_id=self.agent_id,
                recipient_id="story_writer_agent",
                content={"action": "write_story"},
                message_type="request"
            )
            write_result = await self.writer_agent._process_message_impl(write_msg)
            
            # Step 7: Create designs
            logger.info("Step 7/9: Page design")
            design_msg = AgentMessage(
                sender_id=self.agent_id,
                recipient_id="page_design_agent",
                content={"action": "create_page_designs"},
                message_type="request"
            )
            design_result = await self.design_agent._process_message_impl(design_msg)
            
            # Step 8: Review designs
            logger.info("Step 8/9: Design review")
            review_msg = AgentMessage(
                sender_id=self.agent_id,
                recipient_id="design_review_agent",
                content={"action": "review_designs"},
                message_type="request"
            )
            review_result = await self.review_agent._process_message_impl(review_msg)
            
            # Step 9: Generate final book
            logger.info("Step 9/9: Book generation")
            book_msg = AgentMessage(
                sender_id=self.agent_id,
                recipient_id="book_layout_agent",
                content={"action": "generate_book"},
                message_type="request"
            )
            book_result = await self.layout_agent._process_message_impl(book_msg)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Store workflow in KG
            workflow_uri = await self._store_workflow(workflow_id, start_time, end_time, book_result.content.get("book_uri"))
            
            logger.info(f"Book generation complete: {workflow_id} ({duration:.1f}s)")
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "status": "success",
                    "workflow_uri": workflow_uri,
                    "book_uri": book_result.content.get("book_uri"),
                    "html_file": book_result.content.get("html_file"),
                    "duration_seconds": duration,
                },
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))
    
    async def _store_workflow(self, workflow_id: str, start_time: datetime, end_time: datetime, book_uri: str) -> str:
        """Store workflow in KG."""
        workflow_uri = f"http://example.org/workflow/{workflow_id}"
        workflow_ref = URIRef(workflow_uri)
        
        triples = [
            (workflow_ref, RDF.type, BOOK.BookGenerationWorkflow),
            (workflow_ref, PROV.startedAtTime, Literal(start_time.isoformat())),
            (workflow_ref, PROV.endedAtTime, Literal(end_time.isoformat())),
            (workflow_ref, BOOK.workflowStatus, Literal("completed")),
        ]
        
        if book_uri:
            triples.append((workflow_ref, PROV.generated, URIRef(book_uri)))
        
        for triple in triples:
            await self.kg_manager.add_triple(*triple)
        
        return workflow_uri

