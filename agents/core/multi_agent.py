from typing import List, Optional
import time
from agents.core.base_agent import BaseAgent
from kg.models.graph_manager import KnowledgeGraphManager
from agents.core.agent_message import AgentMessage

class MultiAgent(BaseAgent):
    """Agent that can handle multiple capabilities by delegating to sub-agents."""
    
    def __init__(
        self,
        agent_id: str,
        capabilities: List[str],
        sub_agents: List[BaseAgent],
        knowledge_graph: Optional[KnowledgeGraphManager] = None
    ):
        super().__init__(agent_id, capabilities, knowledge_graph)
        self.sub_agents = sub_agents
        self._validate_sub_agents()
        
    def _validate_sub_agents(self):
        """Validate that sub-agents have the required capabilities."""
        sub_agent_capabilities = set()
        for agent in self.sub_agents:
            sub_agent_capabilities.update(agent.capabilities)
            
        missing_capabilities = set(self.capabilities) - sub_agent_capabilities
        if missing_capabilities:
            raise ValueError(
                f"Sub-agents missing required capabilities: {missing_capabilities}"
            )
            
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process a message by delegating to appropriate sub-agents."""
        # Find sub-agents that can handle the message
        capable_agents = [
            agent for agent in self.sub_agents
            if any(cap in agent.capabilities for cap in self.capabilities)
        ]
        
        if not capable_agents:
            raise ValueError(f"No sub-agents can handle capabilities: {self.capabilities}")
            
        # Create response message
        response = AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={},
            timestamp=time.time(),
            message_type="response"
        )
        
        # Process message with each capable agent
        for agent in capable_agents:
            try:
                agent_response = await agent.process_message(message)
                if isinstance(agent_response, AgentMessage):
                    response.content.update(agent_response.content)
            except Exception as e:
                self.logger.error(f"Error processing message with agent {agent.agent_id}: {str(e)}")
                raise
                
        return response 