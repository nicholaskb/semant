from typing import Dict, List, Any, Optional, Set
from loguru import logger
from agents.core.base_agent import BaseAgent, AgentStatus, AgentMessage
from agents.core.capability_types import Capability, CapabilityType, CapabilitySet
from agents.core.agent_factory import AgentFactory
from agents.core.agent_registry import AgentRegistry
import asyncio
import time
from datetime import datetime
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS
import uuid
from datetime import datetime
from agents.core.message_types import AgentMessage

class SupervisorAgent(BaseAgent):
    """Supervisor agent that manages dynamic agent instantiation and role delegation."""
    
    def __init__(
        self,
        agent_id: str,
        registry: AgentRegistry,
        knowledge_graph: Graph,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="supervisor",
            capabilities={
                Capability(CapabilityType.AGENT_MANAGEMENT),
                Capability(CapabilityType.WORKLOAD_MONITORING),
                Capability(CapabilityType.ROLE_DELEGATION)
            },
            config=config
        )
        self.registry = registry
        self.knowledge_graph = knowledge_graph
        self.factory = AgentFactory(registry, knowledge_graph)
        self.logger = logger.bind(agent_id=agent_id, agent_type="supervisor")
        self._monitoring_task = None
        self._is_monitoring = False
        self._workload_threshold = config.get("workload_threshold", 5)
        self._monitoring_interval = config.get("monitoring_interval", 60)  # seconds
        
    async def initialize(self) -> None:
        """Initialize the supervisor agent."""
        await super().initialize()
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitor_workload())
        self.logger.info("Supervisor agent initialized")
        
    async def _monitor_workload(self) -> None:
        """Continuously monitor workload and scale agents as needed."""
        while self._is_monitoring:
            try:
                await self.factory.auto_scale(self._workload_threshold)
                await asyncio.sleep(self._monitoring_interval)
            except Exception as e:
                self.logger.error(f"Error in workload monitoring: {e}")
                await asyncio.sleep(5)  # Wait before retrying
                
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "scale_request":
            return await self._handle_scale_request(message)
        elif message.message_type == "role_change_request":
            return await self._handle_role_change_request(message)
        else:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"error": "Unknown message type"},
                message_type="error"
            )
            
    async def _handle_scale_request(self, message: AgentMessage) -> AgentMessage:
        """Handle requests to scale agent instances."""
        try:
            agent_type = message.content.get("agent_type")
            target_count = message.content.get("target_count")
            
            if not agent_type or not target_count:
                raise ValueError("Missing required parameters")
                
            new_agents = await self.factory.scale_agents(
                agent_type,
                target_count,
                message.content.get("initial_capabilities")
            )
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "status": "success",
                    "new_agents": [agent.agent_id for agent in new_agents]
                },
                message_type="scale_response"
            )
        except Exception as e:
            self.logger.error(f"Error handling scale request: {e}")
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"error": str(e)},
                message_type="error"
            )
            
    async def _handle_role_change_request(self, message: AgentMessage) -> AgentMessage:
        """Handle requests to change agent roles."""
        try:
            agent_id = message.content.get("agent_id")
            new_role = message.content.get("new_role")
            
            if not agent_id or not new_role:
                raise ValueError("Missing required parameters")
                
            await self.factory.delegate_role(
                agent_id,
                new_role,
                message.content.get("additional_capabilities")
            )
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "success"},
                message_type="role_change_response"
            )
        except Exception as e:
            self.logger.error(f"Error handling role change request: {e}")
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"error": str(e)},
                message_type="error"
            )
            
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with supervisor information."""
        supervisor_uri = URIRef(f"agent:{self.agent_id}")
        
        # Update workload threshold
        if "workload_threshold" in update_data:
            self._workload_threshold = update_data["workload_threshold"]
            self.knowledge_graph.add((
                supervisor_uri,
                URIRef("agent:workloadThreshold"),
                Literal(self._workload_threshold)
            ))
            
        # Update monitoring interval
        if "monitoring_interval" in update_data:
            self._monitoring_interval = update_data["monitoring_interval"]
            self.knowledge_graph.add((
                supervisor_uri,
                URIRef("agent:monitoringInterval"),
                Literal(self._monitoring_interval)
            ))
            
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for supervisor-related information."""
        query_type = query.get("type")
        
        if query_type == "workload":
            workload = await self.factory.monitor_workload()
            return {"workload": workload}
        elif query_type == "agent_count":
            agent_counts = {}
            for agent in self.registry.agents.values():
                agent_type = agent.agent_type
                if agent_type not in agent_counts:
                    agent_counts[agent_type] = 0
                agent_counts[agent_type] += 1
            return {"agent_counts": agent_counts}
        else:
            return {"error": "Unknown query type"}
            
    async def cleanup(self) -> None:
        """Clean up resources when shutting down."""
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages - REQUIRED IMPLEMENTATION."""
        try:
            # Process the message based on its type and content
            response_content = f"Agent {self.agent_id} processed: {message.content}"
            
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=response_content,
                message_type=getattr(message, 'message_type', 'response'),
                timestamp=datetime.now()
            )
        except Exception as e:
            # Error handling
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=f"Error processing message: {str(e)}",
                message_type="error",
                timestamp=datetime.now()
            )

        self.logger.info("Supervisor agent cleaned up") 