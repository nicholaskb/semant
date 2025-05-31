from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.reasoner import KnowledgeGraphReasoner
from typing import Dict, Any, List, Optional
import time

class ResearchAgent(BaseAgent):
    """
    Agent that performs advanced reasoning and research investigations using the knowledge graph.
    Message content should include {'topic': ..., 'depth': ...} for research investigations.
    Additional options:
    - require_confidence: bool - Include confidence scoring
    - track_evidence: bool - Track evidence chains
    - explore_paths: bool - Explore multiple research paths
    - use_reasoner: bool - Use advanced reasoning capabilities
    """
    def __init__(self, agent_id: str = "research_agent", capabilities: Optional[List[str]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, "research", capabilities, config)
        self.reasoner = None

    async def initialize(self) -> None:
        """Initialize the agent and its reasoner."""
        self.logger.info("Research Agent initialized")
        if self.knowledge_graph:
            self.reasoner = KnowledgeGraphReasoner(graph=self.knowledge_graph.graph)

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process research investigation requests."""
        topic = message.content.get('topic')
        depth = message.content.get('depth', 2)
        
        if not topic:
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"error": "No research topic provided."},
                timestamp=message.timestamp,
                message_type="research_response"
            )
            
        try:
            # Validate input
            if not isinstance(topic, str):
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"error": "Topic must be a string."},
                    timestamp=message.timestamp,
                    message_type="research_response"
                )
                
            if depth < 0:
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"error": "Depth must be non-negative."},
                    timestamp=message.timestamp,
                    message_type="research_response"
                )
            
            # Perform research investigation
            findings = await self._conduct_research(
                topic,
                depth,
                message.content.get('require_confidence', False),
                message.content.get('track_evidence', False),
                message.content.get('explore_paths', False),
                message.content.get('use_reasoner', False)
            )
            
            # Store findings in knowledge graph
            await self.update_knowledge_graph({
                'subject': f"research:{topic}",
                'predicate': 'hasFindings',
                'object': findings
            })
            
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={
                    "status": "Research investigation completed",
                    "findings": findings
                },
                timestamp=message.timestamp,
                message_type="research_response"
            )
        except Exception as e:
            self.logger.error(f"Error during research investigation: {str(e)}")
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"error": str(e)},
                timestamp=message.timestamp,
                message_type="research_response"
            )

    async def _conduct_research(
        self,
        topic: str,
        depth: int,
        require_confidence: bool,
        track_evidence: bool,
        explore_paths: bool,
        use_reasoner: bool
    ) -> Dict[str, Any]:
        """Conduct research investigation with specified options."""
        findings = {}
        
        # Basic research investigation
        if use_reasoner and self.reasoner:
            findings["reasoning_steps"] = await self.reasoner.investigate_research_topic(topic, depth)
        
        # Explore multiple research paths
        if explore_paths:
            findings["research_paths"] = await self._explore_research_paths(topic, depth)
        
        # Track evidence chain
        if track_evidence:
            findings["evidence_chain"] = await self._build_evidence_chain(topic)
        
        # Calculate confidence score
        if require_confidence:
            confidence_info = await self._calculate_confidence(topic, findings)
            findings["confidence_score"] = confidence_info["score"]
            findings["confidence_factors"] = confidence_info["factors"]
        
        return findings

    async def _explore_research_paths(self, topic: str, depth: int) -> List[Dict[str, Any]]:
        """Explore multiple research paths for a topic."""
        paths = []
        if self.reasoner:
            # Get different aspects of the topic
            aspects = await self.reasoner.find_related_concepts(topic)
            for aspect in aspects:
                path_info = {
                    "path": aspect,
                    "findings": await self.reasoner.investigate_research_topic(aspect, depth)
                }
                paths.append(path_info)
        return paths

    async def _build_evidence_chain(self, topic: str) -> List[Dict[str, Any]]:
        """Build evidence chain for research findings."""
        evidence = []
        if self.reasoner:
            # Get supporting evidence from knowledge graph
            related = await self.reasoner.find_related_concepts(topic)
            for concept in related:
                evidence.append({
                    "source": concept,
                    "supporting_data": await self.reasoner.get_concept_details(concept)
                })
        return evidence

    async def _calculate_confidence(
        self,
        topic: str,
        findings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate confidence score for research findings."""
        score = 0.0
        factors = []
        
        if self.reasoner:
            # Calculate confidence based on evidence strength
            evidence_strength = len(findings.get("evidence_chain", []))
            score += min(evidence_strength / 10, 0.4)  # Up to 40% from evidence
            
            # Calculate confidence based on reasoning steps
            reasoning_steps = len(findings.get("reasoning_steps", []))
            score += min(reasoning_steps / 5, 0.3)  # Up to 30% from reasoning
            
            # Calculate confidence based on research paths
            paths = len(findings.get("research_paths", []))
            score += min(paths / 3, 0.3)  # Up to 30% from multiple paths
            
            factors = [
                {"factor": "evidence_strength", "value": evidence_strength},
                {"factor": "reasoning_steps", "value": reasoning_steps},
                {"factor": "research_paths", "value": paths}
            ]
        
        return {
            "score": min(score, 1.0),  # Ensure score is between 0 and 1
            "factors": factors
        }

    async def query_knowledge_graph(self, query: dict) -> dict:
        """Query the knowledge graph for research-related information."""
        if not self.reasoner:
            return {"error": "Reasoner not initialized"}
            
        try:
            topic = query.get('topic')
            if not topic:
                return {"error": "No topic provided for query"}
                
            # Find related concepts
            related = await self.reasoner.find_related_concepts(topic)
            
            # Get traversal information
            traversal = await self.reasoner.traverse_knowledge_graph(
                topic,
                max_depth=query.get('depth', 2),
                relationship_types=query.get('relationship_types')
            )
            
            result = {
                "related_concepts": related,
                "traversal": traversal
            }
            
            # Include stored findings if requested
            if query.get('include_findings'):
                result["stored_findings"] = await self._get_stored_findings(topic)
            
            return result
        except Exception as e:
            self.logger.error(f"Error querying knowledge graph: {str(e)}")
            return {"error": str(e)}

    async def _get_stored_findings(self, topic: str) -> List[Dict[str, Any]]:
        """Retrieve stored research findings for a topic."""
        findings = []
        if self.knowledge_graph:
            # Query for stored findings
            for s, p, o in self.knowledge_graph.graph:
                if str(s) == f"research:{topic}" and str(p) == "hasFindings":
                    findings.append(o)
        return findings

    async def update_knowledge_graph(self, update_data: dict) -> None:
        """Update the knowledge graph with research findings."""
        try:
            self.logger.info(f"Updating knowledge graph with research findings: {update_data}")
            if self.knowledge_graph:
                await self.knowledge_graph.add_triple(
                    update_data.get('subject', ''),
                    update_data.get('predicate', ''),
                    update_data.get('object', '')
                )
        except Exception as e:
            self.logger.error(f"Error updating knowledge graph: {str(e)}")
            raise 