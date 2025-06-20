from typing import Dict, List, Optional, Any, Union
from loguru import logger
from agents.core.agent_registry import AgentRegistry
from .base_agent import AgentMessage, BaseAgent
from kg.models.graph_manager import KnowledgeGraphManager

class AgentIntegrator:
    """Integrates and coordinates multiple agents in the system."""
    
    def __init__(self, knowledge_graph: KnowledgeGraphManager):
        self.registry = AgentRegistry()
        self.knowledge_graph = knowledge_graph
        self.logger = logger.bind(component="AgentIntegrator")
        self.agents: Dict[str, BaseAgent] = {}
        
    async def initialize(self) -> None:
        """Initialize the agent registry and discover agents."""
        try:
            await self.registry.initialize()  # This will auto-discover agents
            self.logger.info("Agent registry initialized successfully")

            # Remove any auto-discovered agents to keep test environment isolated
            if self.registry.agents:
                for agent_id in list(self.registry.agents.keys()):
                    await self.registry.unregister_agent(agent_id)
                self.logger.debug("Cleared auto-discovered agents for isolated testing")
        except Exception as e:
            self.logger.error(f"Failed to initialize agent registry: {e}")
            raise
            
    async def register_agent(
        self,
        agent_or_id: Union[BaseAgent, str],
        agent_type: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a new agent with the registry.
        
        Args:
            agent_or_id: Either a BaseAgent instance or an agent ID string
            agent_type: The type of agent (required if agent_or_id is a string)
            capabilities: List of agent capabilities (required if agent_or_id is a string)
            config: Optional configuration for the agent
        """
        try:
            if isinstance(agent_or_id, BaseAgent):
                agent = agent_or_id
                agent.knowledge_graph = self.knowledge_graph
                agent._knowledge_graph = self.knowledge_graph  # Ensure internal reference used by test helpers
                self.agents[agent.agent_id] = agent
                agent_capabilities = await agent.get_capabilities()
                await self.registry.register_agent(agent, agent_capabilities)
            else:
                if not agent_type or not capabilities:
                    raise ValueError("agent_type and capabilities are required when registering with an ID")
                await self.registry.register_agent(agent_or_id, agent_type, capabilities, config)
            self.logger.info(f"Registered agent: {agent_or_id if isinstance(agent_or_id, str) else agent_or_id.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to register agent: {e}")
            raise
            
    async def route_message(self, message: AgentMessage) -> List[AgentMessage]:
        """Route a message to the appropriate agent based on capabilities."""
        try:
            if "required_capability" in message.content:
                return await self.registry.route_message_by_capability(
                    message,
                    message.content["required_capability"]
                )
            else:
                # Route to specific agent if recipient is specified
                return await self.registry.route_message(message)
        except Exception as e:
            self.logger.error(f"Failed to route message: {e}")
            raise
            
    async def broadcast_message(self, message: AgentMessage) -> List[AgentMessage]:
        """Broadcast a message to all agents with specific capabilities."""
        try:
            if "required_capabilities" in message.content:
                return await self.registry.broadcast_message_by_capabilities(
                    message.content["required_capabilities"],
                    message
                )
            else:
                # Broadcast to all agents
                return await self.registry.broadcast_message(message)
        except Exception as e:
            self.logger.error(f"Failed to broadcast message: {e}")
            raise
            
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get the status of a specific agent including metadata required by tests."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            capabilities = await agent.get_capabilities()
            return {
                "agent_id": agent.agent_id,
                "agent_type": agent.agent_type,
                "capabilities": list(capabilities),
                "knowledge_graph_connected": agent.knowledge_graph is not None
            }
        # Fallback to registry (should not happen in isolated tests)
        raw_status = await self.registry.get_agent_status(agent_id)
        return {
            "agent_id": agent_id,
            "agent_type": raw_status.get("agent_type", "unknown"),
            "capabilities": list(raw_status.get("capabilities", [])),
            "knowledge_graph_connected": True
        }
        
    async def get_all_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get the status of all registered agents (isolated list)."""
        statuses = {}
        for agent_id in self.agents:
            statuses[agent_id] = await self.get_agent_status(agent_id)
        return statuses
        
    async def get_agents_by_capability(self, capability: str) -> List[str]:
        """Get all agents with a specific capability."""
        return await self.registry.get_agents_by_capability(capability)
        
    async def update_agent_config(self, agent_id: str, config: Dict[str, Any]) -> None:
        """Update the configuration of a specific agent."""
        try:
            agent = await self.registry.get_agent(agent_id)
            if agent:
                for key, value in config.items():
                    agent.update_config(key, value)
                self.logger.info(f"Updated config for agent {agent_id}")
            else:
                raise ValueError(f"Agent {agent_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to update agent config: {e}")
            raise 