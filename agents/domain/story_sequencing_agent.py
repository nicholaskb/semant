"""
Story Sequencing Agent for Children's Book Swarm

Analyzes image pairs and arranges them into a coherent narrative sequence.

Date: 2025-01-08
Status: Implementation
"""

import asyncio
import os
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
    logger.warning("OpenAI library not available")

from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from rdflib import Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

# Namespaces
SCHEMA = Namespace("http://schema.org/")
KG = Namespace("http://example.org/kg#")
BOOK = Namespace("http://example.org/childrens-book#")

# Scoring weights
NARRATIVE_COHERENCE_WEIGHT = 0.4
EMOTIONAL_ARC_WEIGHT = 0.3
VISUAL_VARIETY_WEIGHT = 0.3


class StorySequencingAgent(BaseAgent):
    """
    Agent responsible for arranging image pairs into a narrative sequence.
    
    Workflow:
    1. Query KG for all image pairs
    2. Analyze each input image for narrative potential:
       - Character presence
       - Action/emotion progression
       - Setting changes
    3. Use GPT-4o to propose 3 different sequences
    4. Score each sequence by:
       - Narrative coherence (40%)
       - Emotional arc (30%)
       - Visual variety (30%)
    5. Store best sequence in KG as book:StorySequence
    
    Reuses:
    - GPT-4o for narrative planning
    - PlannerAgent patterns for multi-option generation
    - KnowledgeGraphManager
    """
    
    def __init__(
        self,
        agent_id: str = "story_sequencing_agent",
        capabilities: Optional[set] = None,
        kg_manager: Optional[KnowledgeGraphManager] = None,
    ):
        """
        Initialize the Story Sequencing Agent.
        
        Args:
            agent_id: Unique identifier for this agent
            capabilities: Set of capabilities this agent provides
            kg_manager: Knowledge graph manager instance
        """
        # Convert string capabilities to proper Capability objects
        from agents.core.capability_types import Capability, CapabilityType
        default_capabilities = {"story_sequencing", "narrative_planning", "image_analysis"}
        if capabilities:
            default_capabilities = default_capabilities.union(capabilities)

        capabilities_objects = set()
        for cap_str in default_capabilities:
            try:
                cap_type = CapabilityType(cap_str)
                capabilities_objects.add(Capability(type=cap_type, version="1.0"))
            except ValueError:
                logger.warning(f"Unknown capability type: {cap_str}, skipping")

        super().__init__(
            agent_id=agent_id,
            capabilities=capabilities_objects
        )
        
        if OpenAI is None:
            raise ImportError("OpenAI library required. Install with: pip install openai")
        
        self.kg_manager = kg_manager or KnowledgeGraphManager()
        self.openai_client = OpenAI()
        
        logger.info(
            f"StorySequencingAgent initialized: "
            f"capabilities={self.capabilities}"
        )
    
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """
        Process incoming messages to sequence images into a story.
        
        Expected message content:
        {
            "action": "sequence_story",
            "pair_uris": [...],  # optional, if None sequence all pairs
            "num_proposals": 3  # optional, number of sequences to propose
        }
        
        Returns:
            AgentMessage with results:
            {
                "status": "success",
                "sequence_uri": "...",
                "sequence_order": [...],
                "narrative_arc_score": 0.92,
                "rationale": "Begins with character intro..."
            }
        """
        action = message.content.get("action")
        
        if action == "sequence_story":
            return await self._handle_sequence_story(message)
        else:
            return self._create_error_response(
                message.sender_id,
                f"Unknown action: {action}"
            )
    
    async def _handle_sequence_story(self, message: AgentMessage) -> AgentMessage:
        """Handle the sequence_story action."""
        try:
            # Extract parameters
            pair_uris = message.content.get("pair_uris")
            num_proposals = message.content.get("num_proposals", 3)
            
            logger.info(f"Starting story sequencing: num_proposals={num_proposals}")
            
            # Get image pairs from KG
            if pair_uris is None:
                pairs = await self._get_all_pairs()
            else:
                pairs = await self._get_pairs_by_uris(pair_uris)
            
            logger.info(f"Found {len(pairs)} image pairs to sequence")
            
            if len(pairs) == 0:
                return self._create_error_response(
                    message.sender_id,
                    "No image pairs found to sequence"
                )
            
            # Analyze each pair's narrative potential
            pair_analyses = []
            for pair in pairs:
                analysis = await self._analyze_pair_narrative(pair)
                pair_analyses.append(analysis)
            
            # Generate multiple sequence proposals
            proposals = await self._generate_sequence_proposals(
                pair_analyses=pair_analyses,
                num_proposals=num_proposals
            )
            
            # Score each proposal
            scored_proposals = []
            for proposal in proposals:
                score = await self._score_sequence(proposal, pair_analyses)
                scored_proposals.append({
                    "sequence": proposal,
                    "scores": score,
                    "overall_score": (
                        NARRATIVE_COHERENCE_WEIGHT * score["coherence"] +
                        EMOTIONAL_ARC_WEIGHT * score["emotional_arc"] +
                        VISUAL_VARIETY_WEIGHT * score["visual_variety"]
                    )
                })
            
            # Select best sequence
            best_proposal = max(scored_proposals, key=lambda x: x["overall_score"])
            
            # Store in KG
            sequence_uri = await self._create_sequence_in_kg(
                pair_uris=[pair["uri"] for pair in pairs],
                sequence_order=best_proposal["sequence"],
                scores=best_proposal["scores"],
                rationale=best_proposal.get("rationale", "Best scoring sequence")
            )
            
            logger.info(
                f"Story sequencing complete: "
                f"sequence_uri={sequence_uri}, "
                f"score={best_proposal['overall_score']:.3f}"
            )
            
            # Create response
            response_content = {
                "status": "success",
                "sequence_uri": sequence_uri,
                "sequence_order": best_proposal["sequence"],
                "narrative_arc_score": best_proposal["overall_score"],
                "coherence_score": best_proposal["scores"]["coherence"],
                "emotional_arc_score": best_proposal["scores"]["emotional_arc"],
                "visual_variety_score": best_proposal["scores"]["visual_variety"],
                "rationale": best_proposal.get("rationale", ""),
            }
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=response_content,
                message_type="response",
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error in sequence_story: {e}", exc_info=True)
            return self._create_error_response(message.sender_id, str(e))
    
    async def _get_all_pairs(self) -> List[Dict[str, Any]]:
        """Query KG for all image pairs."""
        query = """
        PREFIX book: <http://example.org/childrens-book#>
        PREFIX schema: <http://schema.org/>
        
        SELECT ?pair ?input ?confidence WHERE {
            ?pair a book:ImagePair ;
                  book:hasInputImage ?input ;
                  book:pairConfidence ?confidence .
            ?input schema:name ?inputName ;
                   schema:description ?inputDesc .
        }
        ORDER BY ?inputName
        """
        
        results = await self.kg_manager.query_graph(query)
        
        pairs = []
        for result in results:
            pairs.append({
                "uri": str(result["pair"]),
                "input_uri": str(result["input"]),
                "confidence": float(result["confidence"]),
            })
        
        return pairs
    
    async def _get_pairs_by_uris(self, uris: List[str]) -> List[Dict[str, Any]]:
        """Query KG for specific pairs by URI."""
        values_clause = " ".join([f"<{uri}>" for uri in uris])
        
        query = f"""
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT ?pair ?input ?confidence WHERE {{
            VALUES ?pair {{ {values_clause} }}
            ?pair a book:ImagePair ;
                  book:hasInputImage ?input ;
                  book:pairConfidence ?confidence .
        }}
        """
        
        results = await self.kg_manager.query_graph(query)
        
        pairs = []
        for result in results:
            pairs.append({
                "uri": str(result["pair"]),
                "input_uri": str(result["input"]),
                "confidence": float(result["confidence"]),
            })
        
        return pairs
    
    async def _analyze_pair_narrative(self, pair: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single image pair for narrative potential.
        
        Uses GPT-4o to identify:
        - Characters present
        - Actions/emotions
        - Setting
        - Narrative elements
        """
        # Get input image description from KG
        input_uri = pair["input_uri"]
        
        query = f"""
        PREFIX schema: <http://schema.org/>
        SELECT ?description WHERE {{
            <{input_uri}> schema:description ?description .
        }}
        """
        
        results = await self.kg_manager.query_graph(query)
        description = str(results[0]["description"]) if results else "No description available"
        
        # Use GPT-4o to analyze narrative potential
        prompt = f"""Analyze this image description for children's book narrative potential:

{description}

Identify:
1. **Characters:** Who or what are the main subjects?
2. **Actions/Emotions:** What is happening? What emotions are conveyed?
3. **Setting:** Where does this take place?
4. **Narrative Role:** Is this an introduction, action, climax, or resolution scene?
5. **Story Potential:** Rate 1-10 how well this works as a story element.

Provide a brief JSON response."""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.5,
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            return {
                "pair_uri": pair["uri"],
                "input_uri": input_uri,
                "description": description,
                "narrative_analysis": analysis_text,
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze pair {pair['uri']}: {e}")
            return {
                "pair_uri": pair["uri"],
                "input_uri": input_uri,
                "description": description,
                "narrative_analysis": "Analysis failed",
            }
    
    async def _generate_sequence_proposals(
        self,
        pair_analyses: List[Dict[str, Any]],
        num_proposals: int
    ) -> List[List[int]]:
        """
        Generate multiple sequence proposals using GPT-4o.
        
        Returns:
            List of proposed sequences (each is a list of pair indices)
        """
        # Build context for GPT-4o
        context = "Here are the image descriptions with narrative analysis:\n\n"
        for i, analysis in enumerate(pair_analyses):
            context += f"Page {i+1}:\n"
            context += f"Description: {analysis['description'][:200]}...\n"
            context += f"Analysis: {analysis['narrative_analysis'][:200]}...\n\n"
        
        prompt = f"""{context}

Create {num_proposals} different sequences for a children's book (ages 3-7).
Each sequence should form a coherent narrative arc.

For each proposal, provide:
1. The page order (list of page numbers)
2. Brief rationale (2-3 sentences)
3. Narrative arc description

Provide response in JSON format:
[
  {{
    "sequence": [1, 3, 2, 4],
    "rationale": "...",
    "arc": "introduction → conflict → resolution"
  }},
  ...
]
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.8,  # Higher temp for creativity
            )
            
            import json
            proposals_json = response.choices[0].message.content.strip()
            
            # Extract JSON (handle markdown code blocks)
            if "```" in proposals_json:
                proposals_json = proposals_json.split("```")[1]
                if proposals_json.startswith("json"):
                    proposals_json = proposals_json[4:]
            
            proposals = json.loads(proposals_json)
            
            # Convert to list of sequences (0-indexed)
            sequences = []
            for proposal in proposals[:num_proposals]:
                sequence = [idx - 1 for idx in proposal["sequence"]]  # Convert to 0-indexed
                sequences.append(sequence)
            
            return sequences
            
        except Exception as e:
            logger.error(f"Failed to generate sequence proposals: {e}")
            # Fallback: return original order
            return [list(range(len(pair_analyses)))]
    
    async def _score_sequence(
        self,
        sequence: List[int],
        pair_analyses: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Score a sequence proposal.
        
        Returns:
            Dict with scores for coherence, emotional_arc, visual_variety
        """
        # Narrative coherence: check for logical ordering
        coherence = self._compute_narrative_coherence(sequence, pair_analyses)
        
        # Emotional arc: check for progression
        emotional_arc = self._compute_emotional_arc(sequence, pair_analyses)
        
        # Visual variety: ensure diverse content
        visual_variety = self._compute_visual_variety(sequence, pair_analyses)
        
        return {
            "coherence": coherence,
            "emotional_arc": emotional_arc,
            "visual_variety": visual_variety,
        }
    
    def _compute_narrative_coherence(
        self,
        sequence: List[int],
        pair_analyses: List[Dict[str, Any]]
    ) -> float:
        """Compute narrative coherence score."""
        if len(sequence) < 2:
            return 1.0  # Single page is always coherent
        
        # Check for sequential vs random jumps
        # Penalize large jumps in sequence
        jumps = [abs(sequence[i+1] - sequence[i]) for i in range(len(sequence)-1)]
        avg_jump = sum(jumps) / len(jumps)
        max_possible_jump = len(sequence) - 1
        
        # Lower jumps = higher coherence
        coherence = 1.0 - (avg_jump / max_possible_jump)
        return max(0.5, coherence)  # Minimum 0.5
    
    def _compute_emotional_arc(
        self,
        sequence: List[int],
        pair_analyses: List[Dict[str, Any]]
    ) -> float:
        """Compute emotional arc score."""
        # Look for emotional progression keywords in analysis
        positive_words = ["happy", "excited", "joyful", "triumphant", "celebration"]
        negative_words = ["sad", "worried", "scared", "problem", "conflict"]
        
        emotions = []
        for idx in sequence:
            if idx < len(pair_analyses):
                text = str(pair_analyses[idx].get("narrative_analysis", "")).lower()
                pos_count = sum(1 for word in positive_words if word in text)
                neg_count = sum(1 for word in negative_words if word in text)
                emotions.append(pos_count - neg_count)
        
        # Good arc: starts neutral/negative, ends positive
        if len(emotions) >= 2:
            if emotions[-1] > emotions[0]:
                return 0.9  # Positive arc
            elif emotions[-1] < emotions[0]:
                return 0.6  # Descending arc (less ideal)
        
        return 0.75  # Neutral/flat arc
    
    def _compute_visual_variety(
        self,
        sequence: List[int],
        pair_analyses: List[Dict[str, Any]]
    ) -> float:
        """Compute visual variety score."""
        # Check for repeated similar descriptions
        descriptions = []
        for idx in sequence:
            if idx < len(pair_analyses):
                desc = str(pair_analyses[idx].get("description", ""))
                descriptions.append(desc)
        
        # Simple variety check: unique words across descriptions
        if not descriptions:
            return 0.5
        
        all_words = set()
        for desc in descriptions:
            words = desc.lower().split()
            all_words.update(words)
        
        # More unique words = more variety
        total_words = sum(len(desc.split()) for desc in descriptions)
        if total_words == 0:
            return 0.5
        
        variety_ratio = len(all_words) / total_words
        return min(1.0, variety_ratio * 2)  # Scale up
    
    async def _create_sequence_in_kg(
        self,
        pair_uris: List[str],
        sequence_order: List[int],
        scores: Dict[str, float],
        rationale: str
    ) -> str:
        """Create a book:StorySequence node in the knowledge graph."""
        sequence_uri = f"http://example.org/story-sequence/{uuid.uuid4()}"
        sequence_ref = URIRef(sequence_uri)
        
        # Create ordered list of pairs
        ordered_pairs = [URIRef(pair_uris[idx]) for idx in sequence_order]
        ordered_list = self.kg_manager.create_rdf_list(ordered_pairs)
        
        # Compute overall narrative arc score
        overall_score = (
            NARRATIVE_COHERENCE_WEIGHT * scores["coherence"] +
            EMOTIONAL_ARC_WEIGHT * scores["emotional_arc"] +
            VISUAL_VARIETY_WEIGHT * scores["visual_variety"]
        )
        
        # Add triples
        triples = [
            # Type
            (sequence_ref, RDF.type, BOOK.StorySequence),
            
            # Ordered pages
            (sequence_ref, BOOK.hasOrderedPages, ordered_list),
            
            # Scores
            (sequence_ref, BOOK.narrativeArcScore, Literal(overall_score, datatype=XSD.float)),
            (sequence_ref, BOOK.coherenceScore, Literal(scores["coherence"], datatype=XSD.float)),
            (sequence_ref, BOOK.emotionalArcScore, Literal(scores["emotional_arc"], datatype=XSD.float)),
            (sequence_ref, BOOK.visualVarietyScore, Literal(scores["visual_variety"], datatype=XSD.float)),
            
            # Rationale
            (sequence_ref, BOOK.sequenceRationale, Literal(rationale)),
            
            # Metadata
            (sequence_ref, SCHEMA.dateCreated, Literal(datetime.utcnow().isoformat(), datatype=XSD.dateTime)),
        ]
        
        # Add to KG
        for triple in triples:
            await self.kg_manager.add_triple(*triple)
        
        logger.debug(f"Created story sequence: {sequence_uri}")
        return sequence_uri


# Standalone function for CLI use
async def sequence_all_pairs() -> Dict[str, Any]:
    """
    Convenience function to sequence all image pairs into a story.
    
    Returns:
        Dict with sequencing results
    """
    agent = StorySequencingAgent()
    
    message = AgentMessage(
        sender_id="cli",
        recipient_id="story_sequencing_agent",
        content={
            "action": "sequence_story",
            "num_proposals": 3,
        },
        message_type="request",
        timestamp=datetime.utcnow().isoformat()
    )
    
    response = await agent._process_message_impl(message)
    return response.content

