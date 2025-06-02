from typing import Dict, List, Any, Optional, Type, Set, Union
from loguru import logger
from agents.core.base_agent import BaseAgent, AgentStatus
from agents.core.capability_types import Capability, CapabilityType, CapabilitySet
from agents.core.agent_registry import AgentRegistry
import asyncio
import time
from datetime import datetime
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS

class AgentFactory:
    """Factory class for creating and managing agent instances dynamically."""
    
    def __init__(self, registry: AgentRegistry, knowledge_graph: Graph):
        self.registry = registry
        self.knowledge_graph = knowledge_graph
        self.logger = logger.bind(component="AgentFactory")
        self._agent_templates: Dict[str, Type[BaseAgent]] = {}
        self._role_requirements: Dict[str, Set[CapabilityType]] = {}
        self._instance_counter = 0
        self._lock = asyncio.Lock()
        
    async def register_agent_template(
        self,
        agent_type: str,
        template_class: Type[BaseAgent],
        required_capabilities: Set[CapabilityType]
    ) -> None:
        """Register a template for creating agents of a specific type."""
        async with self._lock:
            self._agent_templates[agent_type] = template_class
            self._role_requirements[agent_type] = required_capabilities
            self.logger.info(f"Registered agent template for type: {agent_type}")
            # Add to knowledge graph
            agent_type_uri = URIRef(f"agent_type:{agent_type}")
            if hasattr(self.knowledge_graph, 'add_triple'):
                await self.knowledge_graph.add_triple(str(agent_type_uri), str(RDF.type), str(URIRef("agent:AgentType")))
                for capability in required_capabilities:
                    await self.knowledge_graph.add_triple(
                        str(agent_type_uri),
                        str(URIRef("agent:requiresCapability")),
                        str(URIRef(f"capability:{capability}"))
                    )
            else:
                self.knowledge_graph.add((agent_type_uri, RDF.type, URIRef("agent:AgentType")))
                for capability in required_capabilities:
                    self.knowledge_graph.add((
                        agent_type_uri,
                        URIRef("agent:requiresCapability"),
                        URIRef(f"capability:{capability}")
                    ))
    
    async def create_agent(
        self,
        agent_type: str,
        initial_capabilities: Optional[Set[Capability]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseAgent:
        """Create a new agent instance of the specified type."""
        async with self._lock:
            if agent_type not in self._agent_templates:
                raise ValueError(f"Unknown agent type: {agent_type}")
            template_class = self._agent_templates[agent_type]
            required_capabilities = self._role_requirements[agent_type]
            # Generate unique agent ID
            self._instance_counter += 1
            agent_id = f"{agent_type}_{self._instance_counter}"
            # Ensure at least one capability
            if not initial_capabilities:
                initial_capabilities = {Capability(CapabilityType.TASK_EXECUTION, version="1.0")}
            # Create agent instance
            agent = template_class(
                agent_id=agent_id,
                agent_type=agent_type,
                capabilities=initial_capabilities,
                config=config
            )
            # Register agent
            await self.registry.register_agent(agent, initial_capabilities)
            # Add to knowledge graph
            agent_uri = URIRef(f"agent:{agent_id}")
            if hasattr(self.knowledge_graph, 'add_triple'):
                await self.knowledge_graph.add_triple(str(agent_uri), str(RDF.type), str(URIRef(f"agent_type:{agent_type}")))
                await self.knowledge_graph.add_triple(str(agent_uri), str(URIRef("agent:createdAt")), str(Literal(datetime.now())))
                if initial_capabilities:
                    for capability in initial_capabilities:
                        await self.knowledge_graph.add_triple(
                            str(agent_uri),
                            str(URIRef("agent:hasCapability")),
                            str(URIRef(f"capability:{capability.type}"))
                        )
            else:
                self.knowledge_graph.add((agent_uri, RDF.type, URIRef(f"agent_type:{agent_type}")))
                self.knowledge_graph.add((agent_uri, URIRef("agent:createdAt"), Literal(datetime.now())))
                if initial_capabilities:
                    for capability in initial_capabilities:
                        self.knowledge_graph.add((
                            agent_uri,
                            URIRef("agent:hasCapability"),
                            URIRef(f"capability:{capability.type}")
                        ))
            self.logger.info(f"Created new agent instance: {agent_id}")
            return agent
    
    async def delegate_role(
        self,
        agent_id: str,
        new_role: str,
        additional_capabilities: Optional[Set[Capability]] = None
    ) -> None:
        """Delegate a new role to an existing agent."""
        async with self._lock:
            agent = await self.registry.get_agent(agent_id)
            if not agent:
                raise ValueError(f"Agent not found: {agent_id}")
            if new_role not in self._role_requirements:
                raise ValueError(f"Unknown role: {new_role}")
            required_capabilities = self._role_requirements[new_role]
            current_capabilities = await agent.capabilities
            # Add new capabilities if needed
            if additional_capabilities:
                for capability in additional_capabilities:
                    await agent.add_capability(capability)
            # Update agent type
            agent.agent_type = new_role
            # Update knowledge graph
            agent_uri = f"agent:{agent_id}"
            await self.knowledge_graph.add_triple(agent_uri, "agent:roleChangedAt", str(Literal(datetime.now())))
            await self.knowledge_graph.add_triple(agent_uri, "agent:hasRole", f"role:{new_role}")
            await self.knowledge_graph.add_triple(agent_uri, "agent:hasType", new_role)
            self.logger.info(f"[DEBUG] KG triple written: subject={agent_uri}, predicate=agent:hasRole, object=role:{new_role}")
            self.logger.info(f"[DEBUG] KG triple written: subject={agent_uri}, predicate=agent:hasType, object={new_role}")
            self.logger.info(f"Delegated role {new_role} to agent {agent_id}")
    
    async def scale_agents(
        self,
        agent_type: str,
        target_count: int,
        initial_capabilities: Optional[Set[Capability]] = None
    ) -> List[BaseAgent]:
        """Scale the number of agents of a specific type."""
        async with self._lock:
            current_agents = [
                agent for agent in self.registry.agents.values()
                if agent.agent_type == agent_type
            ]
            
            current_count = len(current_agents)
            if current_count == target_count:
                return current_agents
                
            new_agents = []
            if current_count < target_count:
                # Create new agents
                for _ in range(target_count - current_count):
                    agent = await self.create_agent(
                        agent_type,
                        initial_capabilities=initial_capabilities
                    )
                    new_agents.append(agent)
            else:
                # Remove excess agents
                for agent in current_agents[target_count:]:
                    await self.registry.unregister_agent(agent.agent_id)
            
            self.logger.info(
                f"Scaled {agent_type} agents from {current_count} to {target_count}"
            )
            return new_agents
    
    async def monitor_workload(self) -> Dict[str, int]:
        """Monitor current workload distribution across agent types."""
        workload = {}
        for agent in self.registry.agents.values():
            agent_type = agent.agent_type
            if agent_type not in workload:
                workload[agent_type] = 0
            if agent.status == AgentStatus.BUSY:
                workload[agent_type] += 1
        return workload
    
    async def auto_scale(self, workload_threshold: int = 5) -> None:
        """Automatically scale agents based on workload."""
        workload = await self.monitor_workload()
        for agent_type, busy_count in workload.items():
            if busy_count >= workload_threshold:
                # Scale up by 50% of current count
                current_count = len([
                    a for a in self.registry.agents.values()
                    if a.agent_type == agent_type
                ])
                target_count = current_count + (current_count // 2)
                await self.scale_agents(agent_type, target_count)
                self.logger.info(
                    f"Auto-scaled {agent_type} agents from {current_count} to {target_count}"
                ) 