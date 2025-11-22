"""
Story Writer Agent for Children's Book Swarm
Date: 2025-01-08
TaskMaster Task #106

Generates age-appropriate story text for each page.
Research-driven approach using children's book writing best practices.

REUSES (NO DUPLICATES):
- agents/core/base_agent.py - BaseAgent
- agents/domain/image_analysis_agent.py - ImageAnalysisAgent
- kg/models/graph_manager.py - KnowledgeGraphManager
- OpenAI GPT-4o (DiaryAgent pattern)
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

# ✅ REUSE: BaseAgent
from agents.core.base_agent import BaseAgent, AgentMessage

# ✅ REUSE: KG Manager
from kg.models.graph_manager import KnowledgeGraphManager

# ✅ REUSE: ImageAnalysisAgent
from agents.domain.image_analysis_agent import ImageAnalysisAgent

# ✅ REUSE: OpenAI (DiaryAgent pattern)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# ✅ REUSE: RDFLib
from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD

BOOK = Namespace("http://example.org/childrens-book#")


class StoryWriterAgent(BaseAgent):
    """
    Generates age-appropriate story text for children's book pages.
    
    Research Phase:
    - Queries GPT-4o for children's book writing best practices (ages 3-7)
    - Learns about vocabulary, sentence structure, pacing
    
    Writing Guidelines:
    - Target: 50-100 words per page
    - Reading level: Grade K-1
    - Simple vocabulary
    - Short sentences
    - Repetition for rhythm
    - Emotional engagement
    
    Reuses:
    - BaseAgent, ImageAnalysisAgent, KnowledgeGraphManager
    - OpenAI client (same pattern as DiaryAgent)
    """
    
    def __init__(
        self,
        agent_id: str = "story_writer_agent",
        kg_manager: Optional[KnowledgeGraphManager] = None,
        target_age: str = "3-7",
    ):
        super().__init__(agent_id=agent_id)
        self.kg_manager = kg_manager or KnowledgeGraphManager()
        self.target_age = target_age
        
        if not OpenAI:
            raise ImportError("OpenAI required")
        self.openai_client = OpenAI()
        self.writing_guidelines = None
        
        logger.info(f"StoryWriterAgent initialized: target_age={target_age}")
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        action = message.content.get("action")
        
        if action == "write_story":
            return await self._handle_write_story(message)
        return self._create_error_response(message.sender_id, f"Unknown action: {action}")
    
    async def _handle_write_story(self, message: AgentMessage) -> AgentMessage:
        try:
            logger.info(f"{self.agent_id}: Starting story writing")
            
            # Research if needed
            if not self.writing_guidelines:
                self.writing_guidelines = await self._research_writing_guidelines()
            
            # Get story sequence
            sequence = await self._get_story_sequence()
            if not sequence:
                return self._create_error_response(message.sender_id, "No story sequence found")
            
            # Write text for each page
            pages_with_text = []
            for idx, page in enumerate(sequence["pages"]):
                text = await self._write_page_text(page, idx, len(sequence["pages"]))
                await self._store_text_in_kg(page["pair_uri"], text, idx + 1)
                pages_with_text.append({"pair_uri": page["pair_uri"], "text": text})
            
            logger.info(f"{self.agent_id}: Wrote text for {len(pages_with_text)} pages")
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "status": "success",
                    "pages_written": len(pages_with_text),
                    "pages": pages_with_text,
                },
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"{self.agent_id}: Error: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))
    
    async def _research_writing_guidelines(self) -> str:
        """Research children's book writing using GPT-4o."""
        prompt = f"""
        What are the best practices for writing children's books for ages {self.target_age}?
        
        Focus on:
        1. Vocabulary level and word choice
        2. Sentence structure and length
        3. Pacing and rhythm
        4. Emotional engagement
        5. Use of repetition and patterns
        
        Provide actionable guidelines for writing compelling, age-appropriate text.
        """
        
        response = self.openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        
        return response.choices[0].message.content.strip()
    
    async def _get_story_sequence(self) -> Optional[Dict[str, Any]]:
        """Get the story sequence from KG."""
        query = """
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT ?sequence
        WHERE {
            ?sequence a book:StorySequence .
        }
        LIMIT 1
        """
        
        results = await self.kg_manager.query_graph(query)
        if not results:
            return None
        
        sequence_uri = str(results[0]["sequence"])
        
        # Get ordered pages
        pages_query = f"""
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT ?pair ?order
        WHERE {{
            <{sequence_uri}> book:hasPage ?pair .
            ?pair book:sequenceOrder ?order .
        }}
        ORDER BY ?order
        """
        
        page_results = await self.kg_manager.query_graph(pages_query)
        
        pages = []
        for r in page_results:
            # Get image description
            desc_query = f"""
            PREFIX book: <http://example.org/childrens-book#>
            PREFIX schema: <http://schema.org/>
            
            SELECT ?input ?description
            WHERE {{
                <{r['pair']}> book:hasInputImage ?input .
                ?input schema:description ?description .
            }}
            """
            desc_results = await self.kg_manager.query_graph(desc_query)
            
            description = str(desc_results[0]["description"]) if desc_results else ""
            
            pages.append({
                "pair_uri": str(r["pair"]),
                "order": int(r["order"]),
                "description": description,
            })
        
        return {"sequence_uri": sequence_uri, "pages": pages}
    
    async def _write_page_text(
        self,
        page: Dict[str, Any],
        page_index: int,
        total_pages: int
    ) -> str:
        """Write story text for one page."""
        position = "beginning" if page_index == 0 else ("end" if page_index == total_pages - 1 else "middle")
        
        prompt = f"""
        Write text for page {page_index + 1} of {total_pages} in a children's book (ages {self.target_age}).
        
        Guidelines:
        {self.writing_guidelines}
        
        Image description: {page['description']}
        
        Position in story: {position}
        
        Requirements:
        - 50-100 words
        - Grade K-1 reading level
        - Simple, engaging language
        - Match the image content
        - Create emotional connection
        
        Write ONLY the story text, no labels or explanations.
        """
        
        response = self.openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=200,
        )
        
        text = response.choices[0].message.content.strip()
        word_count = len(text.split())
        
        logger.debug(f"{self.agent_id}: Wrote {word_count} words for page {page_index + 1}")
        return text
    
    async def _store_text_in_kg(self, pair_uri: str, text: str, page_num: int) -> None:
        """Store story text in KG."""
        pair_ref = URIRef(pair_uri)
        word_count = len(text.split())
        
        triples = [
            (pair_ref, BOOK.hasStoryText, Literal(text)),
            (pair_ref, BOOK.textWordCount, Literal(word_count, datatype=XSD.integer)),
            (pair_ref, BOOK.readingLevel, Literal("Grade K-1")),
        ]
        
        for triple in triples:
            await self.kg_manager.add_triple(*triple)


async def write_story_for_book() -> Dict[str, Any]:
    """Standalone function to write story."""
    agent = StoryWriterAgent()
    message = AgentMessage(
        sender_id="cli",
        recipient_id="story_writer_agent",
        content={"action": "write_story"},
        message_type="request",
        timestamp=datetime.utcnow().isoformat()
    )
    response = await agent._process_message_impl(message)
    return response.content

