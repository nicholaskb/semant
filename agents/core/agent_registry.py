from typing import Dict, List, Any, Optional, Type, Set, Union, Callable
from loguru import logger
from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.capability_types import Capability, CapabilityType, CapabilitySet
import importlib
import inspect
import os
import yaml
from pathlib import Path
import sys
import asyncio
from collections import defaultdict
from abc import ABC, abstractmethod
from .base_agent import AgentStatus

class WorkflowNotifier:
    """Handles notifications between components."""
    def __init__(self):
        self._subscribers: Dict[str, Set[Callable]] = defaultdict(set)
        self._notification_queue = asyncio.Queue()
        self._notification_worker = asyncio.create_task(self._process_notifications())
        self.logger = logger.bind(component="WorkflowNotifier")
    
    async def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to specific event types."""
        self._subscribers[event_type].add(callback)
        self.logger.debug(f"New subscriber for {event_type}")
    
    async def notify_capability_change(
        self,
        agent_id: str,
        new_capabilities: Set[Capability]
    ) -> None:
        """Notify about capability changes."""
        await self._notification_queue.put({
            "type": "capability_change",
            "agent_id": agent_id,
            "capabilities": new_capabilities
        })
        self.logger.debug(f"Notified capability change for agent {agent_id}")
    
    async def notify_workflow_assembled(
        self,
        workflow_id: str,
        agents: List[str]
    ) -> None:
        """Notify about workflow assembly."""
        await self._notification_queue.put({
            "type": "workflow_assembled",
            "workflow_id": workflow_id,
            "agents": agents
        })
        self.logger.debug(f"Notified workflow assembly for {workflow_id}")
    
    async def _process_notifications(self) -> None:
        """Process notifications in the background."""
        while True:
            try:
                notification = await self._notification_queue.get()
                event_type = notification["type"]
                if event_type in self._subscribers:
                    for callback in self._subscribers[event_type]:
                        try:
                            await callback(notification)
                        except Exception as e:
                            self.logger.error(f"Error in notification callback: {e}")
            except Exception as e:
                self.logger.error(f"Error processing notification: {e}")
            finally:
                self._notification_queue.task_done()

    async def shutdown(self):
        """Gracefully shut down the notification worker."""
        self._notification_worker.cancel()
        try:
            await self._notification_worker
        except asyncio.CancelledError:
            pass

class RegistryObserver(ABC):
    """Observer interface for registry changes."""
    
    @abstractmethod
    async def on_agent_registered(self, agent: BaseAgent) -> None:
        """Called when an agent is registered."""
        pass
        
    @abstractmethod
    async def on_agent_deregistered(self, agent_id: str) -> None:
        """Called when an agent is deregistered."""
        pass
        
    @abstractmethod
    async def on_capability_updated(self, agent_id: str, capabilities: Set[Capability]) -> None:
        """Called when an agent's capabilities are updated."""
        pass

class AgentRegistry:
    """Manages agent registration and capability mapping."""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._capability_map: Dict[CapabilityType, Set[str]] = defaultdict(set)
        self._agent_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._capability_locks: Dict[CapabilityType, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._workflow_notifier = WorkflowNotifier()
        self._observers: List[RegistryObserver] = []
        self.logger = logger.bind(component="AgentRegistry")
        asyncio.create_task(self._auto_discover_agents())
        
    async def discover_agents(self, config_path: Optional[str] = None) -> None:
        """Discover and register agents from configuration or auto-discovery."""
        if config_path and os.path.exists(config_path):
            await self._load_from_config(config_path)
        else:
            await self._auto_discover_agents()
            
    async def _load_from_config(self, config_path: str) -> None:
        """Load agent configurations from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            for agent_config in config.get('agents', []):
                agent_type = agent_config.get('type')
                agent_id = agent_config.get('id')
                capabilities = set(agent_config.get('capabilities', []))
                
                if agent_type in self.agent_types:
                    agent = self.agent_types[agent_type](agent_id)
                    await self.register_agent(agent, capabilities)
                else:
                    self.logger.warning(f"Unknown agent type: {agent_type}")
        except Exception as e:
            self.logger.error(f"Failed to load agent config: {e}")
            raise
            
    async def _auto_discover_agents(self) -> None:
        """Auto-discover available agent types."""
        try:
            for name, obj in inspect.getmembers(sys.modules[__name__]):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseAgent) and 
                    obj != BaseAgent):
                    self.logger.info(f"Discovered agent type: {name}")
        except Exception as e:
            self.logger.error(f"Error in agent discovery: {e}")
            
    async def register_agent(self, agent: BaseAgent, capabilities: Set[Capability]) -> None:
        """Register agent with thread-safe capability handling."""
        async with self._agent_locks[agent.agent_id]:
            if agent.agent_id in self._agents:
                self.logger.warning(f"Agent {agent.agent_id} already registered")
                return
            
            self._agents[agent.agent_id] = agent
            for capability in capabilities:
                async with self._capability_locks[capability.type]:
                    self._capability_map[capability.type].add(agent.agent_id)
            
            await self._workflow_notifier.notify_capability_change(agent.agent_id, capabilities)
            self.logger.info(f"Registered agent {agent.agent_id} with capabilities: {capabilities}")
            
            # Notify observers
            for observer in self._observers:
                try:
                    await observer.on_agent_registered(agent)
                except Exception as e:
                    self.logger.error(f"Error notifying observer of agent registration: {e}")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister agent and clean up capability mappings."""
        async with self._agent_locks[agent_id]:
            if agent_id not in self._agents:
                self.logger.warning(f"Agent {agent_id} not found")
                return
            
            agent = self._agents[agent_id]
            agent_capabilities = await agent.capabilities
            
            for capability in agent_capabilities:
                async with self._capability_locks[capability.type]:
                    self._capability_map[capability.type].discard(agent_id)
                    if not self._capability_map[capability.type]:
                        del self._capability_map[capability.type]
            
            del self._agents[agent_id]
            self.logger.info(f"Unregistered agent: {agent_id}")
            
            # Notify observers
            for observer in self._observers:
                try:
                    await observer.on_agent_deregistered(agent_id)
                except Exception as e:
                    self.logger.error(f"Error notifying observer of agent deregistration: {e}")
    
    async def get_agents_by_capability(self, capability_type: CapabilityType) -> List[BaseAgent]:
        """Get all agents with a specific capability."""
        async with self._capability_locks[capability_type]:
            agent_ids = self._capability_map.get(capability_type, set())
            return [self._agents[agent_id] for agent_id in agent_ids if agent_id in self._agents]
    
    async def get_agent_capabilities(self, agent_id: str) -> Set[Capability]:
        """Get all capabilities for an agent."""
        async with self._agent_locks[agent_id]:
            if agent_id not in self._agents:
                return set()
            return await self._agents[agent_id].capabilities
    
    async def update_agent_capabilities(
        self,
        agent_id: str,
        new_capabilities: Set[Capability]
    ) -> None:
        """Update agent capabilities with proper synchronization."""
        async with self._agent_locks[agent_id]:
            if agent_id not in self._agents:
                self.logger.warning(f"Agent {agent_id} not found")
                return
            
            agent = self._agents[agent_id]
            old_capabilities = await agent.capabilities
            
            # Remove old capabilities
            for capability in old_capabilities:
                async with self._capability_locks[capability.type]:
                    self._capability_map[capability.type].discard(agent_id)
                    if not self._capability_map[capability.type]:
                        del self._capability_map[capability.type]
            
            # Add new capabilities
            for capability in new_capabilities:
                async with self._capability_locks[capability.type]:
                    self._capability_map[capability.type].add(agent_id)
            
            # Update agent capabilities
            for capability in old_capabilities:
                await agent.remove_capability(capability)
            for capability in new_capabilities:
                await agent.add_capability(capability)
            
            await self._workflow_notifier.notify_capability_change(agent_id, new_capabilities)
            self.logger.info(f"Updated capabilities for agent {agent_id}: {new_capabilities}")
            
            # Notify observers
            for observer in self._observers:
                try:
                    await observer.on_capability_updated(agent_id, new_capabilities)
                except Exception as e:
                    self.logger.error(f"Error notifying observer of capability update: {e}")
    
    async def subscribe_to_notifications(self, event_type: str, callback: Callable) -> None:
        """Subscribe to registry notifications."""
        await self._workflow_notifier.subscribe(event_type, callback)
    
    async def validate_capabilities(self, required_capabilities: Set[Capability]) -> Dict[str, Any]:
        """Validate if all required capabilities are available."""
        missing_capabilities = set()
        for capability in required_capabilities:
            async with self._capability_locks[capability.type]:
                if not self._capability_map[capability.type]:
                    missing_capabilities.add(capability)
        
        return {
            "is_valid": len(missing_capabilities) == 0,
            "missing_capabilities": missing_capabilities
        }
        
    async def route_message_by_capability(
        self,
        message: AgentMessage,
        required_capability: CapabilityType
    ) -> List[AgentMessage]:
        """Route a message to all agents with a specific capability."""
        responses = []
        capable_agents = await self.get_agents_by_capability(required_capability)
        
        for agent in capable_agents:
            if agent.agent_id != message.sender:  # Don't send to self
                response = await agent.process_message(message)
                responses.append(response)
                
        return responses
        
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get the status of a specific agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return {"error": f"Agent not found: {agent_id}"}
            
        return {
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type,
            "capabilities": await self.get_agent_capabilities(agent_id),
            "diary_entries": len(agent.diary),
            "knowledge_graph_connected": agent.knowledge_graph is not None
        }
        
    async def get_all_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get the status of all registered agents."""
        return {
            agent_id: await self.get_agent_status(agent_id)
            for agent_id in self._agents
        }
        
    async def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by its ID."""
        return self._agents.get(agent_id)

    async def route_message(self, message: AgentMessage) -> AgentMessage:
        """Route a message to the agent specified by recipient or capability."""
        if "required_capability" in message.content:
            # Route by capability
            capable_agents = await self.get_agents_by_capability(message.content["required_capability"])
            if not capable_agents:
                raise ValueError(f"No agents found with capability: {message.content['required_capability']}")
            # Use the first capable agent
            return await capable_agents[0].process_message(message)
        else:
            # Route by recipient
            recipient_id = message.recipient
            agent = self._agents.get(recipient_id)
            if not agent:
                raise ValueError(f"Agent not found: {recipient_id}")
            return await agent.process_message(message)

    async def broadcast_message(self, message: AgentMessage) -> List[AgentMessage]:
        """Broadcast a message to all agents except the sender."""
        responses = []
        for agent_id, agent in self._agents.items():
            if agent_id != message.sender:
                response = await agent.process_message(message)
                responses.append(response)
        return responses

    def add_observer(self, observer: RegistryObserver) -> None:
        """Add an observer to the registry."""
        if observer not in self._observers:
            self._observers.append(observer)
            
    def remove_observer(self, observer: RegistryObserver) -> None:
        """Remove an observer from the registry."""
        if observer in self._observers:
            self._observers.remove(observer)
            
    async def clear(self) -> None:
        """Clear all registered agents."""
        async with self._agent_locks:
            self._agents.clear()
            self._capability_map.clear()
            self.logger.info("Cleared all registered agents")

    async def shutdown(self):
        await self._workflow_notifier.shutdown() 