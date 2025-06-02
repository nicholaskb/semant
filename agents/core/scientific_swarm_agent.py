from typing import Dict, Any, List, Optional, Set
from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from loguru import logger
import asyncio
from datetime import datetime

class ScientificSwarmAgent(BaseAgent):
    """
    Base class for scientific coding swarm agents.
    These agents collaborate through the knowledge graph to perform code reviews,
    generate tests, analyze performance, and ensure code quality.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "scientific_swarm",
        capabilities: Optional[Set[Capability]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(agent_id, agent_type, capabilities, config)
        self.review_history: List[Dict[str, Any]] = []
        if config is None:
            config = {}
        self.consensus_threshold = config.get('consensus_threshold', 0.75)
        self.min_reviewers = config.get('min_reviewers', 2)
        
    async def initialize(self) -> None:
        """Initialize the scientific swarm agent."""
        await super().initialize()
        self.logger.info("Scientific Swarm Agent initialized")
        
        # Register agent in knowledge graph
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph({
                f"agent:{self.agent_id}": {
                    "rdf:type": "swarm:ScientificSwarmAgent",
                    "swarm:hasStatus": "swarm:Active",
                    "swarm:consensusThreshold": str(self.consensus_threshold),
                    "swarm:minReviewers": str(self.min_reviewers)
                }
            })
            
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages for scientific code review and analysis."""
        try:
            if message.message_type == "review_request":
                return await self._handle_review_request(message)
            elif message.message_type == "consensus_check":
                return await self._handle_consensus_check(message)
            elif message.message_type == "code_analysis":
                return await self._handle_code_analysis(message)
            else:
                return await self._handle_unknown_message(message)
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"error": str(e)},
                timestamp=message.timestamp,
                message_type="error"
            )
            
    async def _handle_review_request(self, message: AgentMessage) -> AgentMessage:
        """Handle code review requests."""
        try:
            code_artifact = message.content.get('code_artifact')
            if not code_artifact:
                raise ValueError("No code artifact provided for review")
                
            # Perform review based on agent's capabilities
            review_result = await self._perform_review(code_artifact)
            
            # Store review in history
            self.review_history.append({
                'timestamp': datetime.now().isoformat(),
                'artifact': code_artifact,
                'result': review_result
            })
            
            # Update knowledge graph
            if self.knowledge_graph:
                await self.knowledge_graph.update_graph({
                    f"review:{code_artifact}": {
                        "rdf:type": "review:Review",
                        "review:reviewedBy": f"agent:{self.agent_id}",
                        "review:timestamp": datetime.now().isoformat(),
                        "review:result": str(review_result)
                    }
                })
                
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"review_result": review_result},
                timestamp=message.timestamp,
                message_type="review_response"
            )
        except Exception as e:
            self.logger.error(f"Error handling review request: {str(e)}")
            raise
            
    async def _handle_consensus_check(self, message: AgentMessage) -> AgentMessage:
        """Handle consensus check requests."""
        try:
            artifact_id = message.content.get('artifact_id')
            if not artifact_id:
                raise ValueError("No artifact ID provided for consensus check")
                
            # Query knowledge graph for all reviews
            if self.knowledge_graph:
                reviews = await self.knowledge_graph.query_graph(f"""
                    SELECT ?reviewer ?result
                    WHERE {{
                        ?review rdf:type review:Review ;
                               review:reviewedBy ?reviewer ;
                               review:result ?result .
                        FILTER(?review = <review:{artifact_id}>)
                    }}
                """)
                
                # Calculate consensus
                consensus = await self._calculate_consensus(reviews)
                
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"consensus": consensus},
                    timestamp=message.timestamp,
                    message_type="consensus_response"
                )
        except Exception as e:
            self.logger.error(f"Error handling consensus check: {str(e)}")
            raise
            
    async def _handle_code_analysis(self, message: AgentMessage) -> AgentMessage:
        """Handle code analysis requests."""
        try:
            code = message.content.get('code')
            analysis_type = message.content.get('analysis_type')
            if not code or not analysis_type:
                raise ValueError("Code and analysis type required")
                
            # Perform analysis based on type
            analysis_result = await self._perform_analysis(code, analysis_type)
            
            # Update knowledge graph
            if self.knowledge_graph:
                await self.knowledge_graph.update_graph({
                    f"analysis:{analysis_type}": {
                        "rdf:type": f"analysis:{analysis_type}",
                        "analysis:performedBy": f"agent:{self.agent_id}",
                        "analysis:timestamp": datetime.now().isoformat(),
                        "analysis:result": str(analysis_result)
                    }
                })
                
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"analysis_result": analysis_result},
                timestamp=message.timestamp,
                message_type="analysis_response"
            )
        except Exception as e:
            self.logger.error(f"Error handling code analysis: {str(e)}")
            raise
            
    async def _perform_review(self, code_artifact: Dict[str, Any]) -> Dict[str, Any]:
        """Perform code review based on agent's capabilities."""
        review_result = {
            'status': 'pending',
            'findings': [],
            'recommendations': []
        }
        
        # Implement review logic based on capabilities
        if await self.has_capability(CapabilityType.CODE_REVIEW):
            # Add code review findings
            pass
            
        if await self.has_capability(CapabilityType.TEST_GENERATION):
            # Add test coverage analysis
            pass
            
        if await self.has_capability(CapabilityType.PERFORMANCE_ANALYSIS):
            # Add performance analysis
            pass
            
        return review_result
        
    async def _calculate_consensus(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate consensus from multiple reviews."""
        if not reviews:
            return {'has_consensus': False, 'reason': 'No reviews found'}
            
        # Count approvals and rejections
        approvals = sum(1 for r in reviews if r.get('result', {}).get('status') == 'approved')
        total = len(reviews)
        
        consensus = {
            'has_consensus': False,
            'approval_rate': approvals / total,
            'total_reviews': total,
            'required_reviews': self.min_reviewers,
            'required_threshold': self.consensus_threshold
        }
        
        # Check if consensus is reached
        if total >= self.min_reviewers and (approvals / total) >= self.consensus_threshold:
            consensus['has_consensus'] = True
            
        return consensus
        
    async def _perform_analysis(self, code: str, analysis_type: str) -> Dict[str, Any]:
        """Perform code analysis based on type."""
        analysis_result = {
            'type': analysis_type,
            'timestamp': datetime.now().isoformat(),
            'findings': []
        }
        
        # Implement analysis based on type
        if analysis_type == 'performance':
            if await self.has_capability(CapabilityType.PERFORMANCE_ANALYSIS):
                # Add performance analysis
                pass
                
        elif analysis_type == 'security':
            if await self.has_capability(CapabilityType.SECURITY_ANALYSIS):
                # Add security analysis
                pass
                
        elif analysis_type == 'architecture':
            if await self.has_capability(CapabilityType.ARCHITECTURE_REVIEW):
                # Add architecture analysis
                pass
                
        return analysis_result
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with scientific coding information."""
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph(update_data)
            
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for scientific coding information."""
        if not self.knowledge_graph:
            return {}
        return await self.knowledge_graph.query_graph(query.get('sparql', '')) 