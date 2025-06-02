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
import time
from datetime import datetime

class RegistryObserver(ABC):
    """Abstract base class for registry observers."""
    
    @abstractmethod
    async def on_agent_registered(self, agent_id: str) -> None:
        """Called when an agent is registered."""
        pass
        
    @abstractmethod
    async def on_agent_unregistered(self, agent_id: str) -> None:
        """Called when an agent is unregistered."""
        pass
        
    @abstractmethod
    async def on_capability_updated(self, agent_id: str, capabilities: Set[Capability]) -> None:
        """Called when an agent's capabilities are updated."""
        pass

class WorkflowNotifier:
    """Handles notifications between components."""
    
    def __init__(self):
        self._notification_queue = None
        self._recovery_locks = {}
        self._tasks = set()
        self.logger = logger.bind(component="WorkflowNotifier")
        
    async def initialize(self):
        """Initialize the notification system."""
        if not self._notification_queue:
            self._notification_queue = asyncio.Queue()
            self._start_notification_processor()
            
    def _start_notification_processor(self):
        """Start the notification processing task."""
        task = asyncio.create_task(self._process_notifications())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        
    async def _process_notifications(self):
        """Process notifications from the queue."""
        try:
            while True:
                notification = await self._notification_queue.get()
                try:
                    if notification["type"] == "agent_recovery":
                        await self._handle_recovery_notification(notification)
                    elif notification["type"] == "capability_change":
                        await self._handle_capability_notification(notification)
                    elif notification["type"] == "workflow_assembled":
                        await self._handle_workflow_notification(notification)
                except Exception as e:
                    self.logger.error(f"Error processing notification: {e}")
                finally:
                    self._notification_queue.task_done()
        except asyncio.CancelledError:
            self.logger.info("Notification processor cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in notification processor: {e}")
            raise
            
    async def _handle_recovery_notification(self, notification):
        """Handle agent recovery notifications."""
        agent_id = notification["agent_id"]
        success = notification["success"]
        timestamp = notification["timestamp"]
        
        async with self._recovery_locks.get(agent_id, asyncio.Lock()):
            self.logger.info(f"Processing recovery notification for {agent_id}: {success}")
            # Additional recovery handling logic here
            
    async def _handle_capability_notification(self, notification):
        """Handle capability change notifications."""
        agent_id = notification["agent_id"]
        capabilities = notification["capabilities"]
        self.logger.info(f"Processing capability change for {agent_id}: {capabilities}")
        # Additional capability handling logic here

    async def _handle_workflow_notification(self, notification):
        """Handle workflow assembly notifications."""
        workflow_id = notification["workflow_id"]
        agents = notification["agents"]
        self.logger.info(f"Processing workflow assembly for {workflow_id}: {agents}")
        # Additional workflow handling logic here
            
    async def cleanup(self):
        """Clean up notification tasks."""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
    async def notify_agent_recovery(self, agent_id: str, success: bool) -> None:
        """Notify about agent recovery status."""
        if not self._notification_queue:
            await self.initialize()
            
        if agent_id not in self._recovery_locks:
            self._recovery_locks[agent_id] = asyncio.Lock()
            
        async with self._recovery_locks[agent_id]:
            await self._notification_queue.put({
                "type": "agent_recovery",
                "agent_id": agent_id,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            })
            self.logger.debug(f"Notified agent recovery for {agent_id}: {success}")
    
    async def notify_capability_change(
        self,
        agent_id: str,
        new_capabilities: Set[Capability]
    ) -> None:
        """Notify about capability changes."""
        if not self._notification_queue:
            await self.initialize()
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
        if not self._notification_queue:
            await self.initialize()
        await self._notification_queue.put({
            "type": "workflow_assembled",
            "workflow_id": workflow_id,
            "agents": agents
        })
        self.logger.debug(f"Notified workflow assembly for {workflow_id}")
    
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
        """Shutdown the notification system."""
        self.logger.info("Shutting down WorkflowNotifier")
        await self.cleanup()
        if self._notification_queue:
            await self._notification_queue.join()
        self.logger.info("WorkflowNotifier shutdown complete")

class AgentRegistry:
    """Manages agent registration and capability mapping."""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._capability_map: Dict[CapabilityType, Set[str]] = defaultdict(set)
        self._agent_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._capability_locks: Dict[CapabilityType, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._workflow_notifier = WorkflowNotifier()
        self._observers: List[RegistryObserver] = []
        self._capability_cache = {}
        self._cache_ttl = 60  # Cache TTL in seconds
        self._last_cache_update = time.time()
        self.logger = logger.bind(component="AgentRegistry")
        self._discovery_task = None
        self._is_initialized = False
        print(f"[DEBUG] AgentRegistry initialized. _agents: {self._agents}, _capability_map: {self._capability_map}")
    
    async def initialize(self):
        """Initialize the agent registry."""
        if not self._is_initialized:
            await self._workflow_notifier.initialize()
            self._discovery_task = asyncio.create_task(self._auto_discover_agents())
            self._is_initialized = True
            logger.debug(f"AgentRegistry initialized. _agents: {self._agents}, _capability_map: {self._capability_map}")
            
    async def cleanup(self) -> None:
        """Clean up resources and cancel pending tasks."""
        self.logger.info("Starting cleanup of AgentRegistry")
        
        # Cancel all tasks
        tasks = []
        if hasattr(self, '_discovery_task'):
            tasks.append(self._discovery_task)
            
        # Cancel tasks
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        # Clear collections
        self._agents.clear()
        self._capability_map.clear()
        self._agent_locks.clear()
        self._capability_locks.clear()
        
        # Shutdown notifier
        try:
            await self._workflow_notifier.cleanup()
        except Exception as e:
            self.logger.error(f"Error during notifier cleanup: {e}")
            
        self.logger.info("AgentRegistry cleanup completed")

    def __del__(self):
        """Cleanup when the object is destroyed."""
        if self._discovery_task and not self._discovery_task.done():
            self._discovery_task.cancel()
    
    @property
    def agents(self) -> Dict[str, BaseAgent]:
        """Get all registered agents."""
        return self._agents
        
    async def discover_agents(self, config_path: Optional[str] = None) -> None:
        """Discover and register agents from configuration or auto-discovery."""
        if not self._discovery_task:
            await self.initialize()
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
            
    async def register_agent(self, agent: BaseAgent, capabilities: Optional[Set[Capability]] = None) -> None:
        """Register agent with thread-safe capability handling."""
        print(f"[DEBUG] Before registration - _agents: {self._agents}")
        
        # Validate agent
        if not agent or not agent.agent_id:
            raise ValueError("Invalid agent: agent_id is required")
            
        # Get and validate capabilities
        if capabilities is None:
            capabilities = await agent.capabilities
            
        # Validate capabilities
        if not capabilities:
            raise ValueError(f"Agent {agent.agent_id} must have at least one capability")
            
        if not all(isinstance(c, Capability) for c in capabilities):
            raise TypeError("All capabilities must be Capability instances")
            
        async with self._agent_locks[agent.agent_id]:
            if agent.agent_id in self._agents:
                self.logger.warning(f"Agent {agent.agent_id} already registered, updating capabilities")
            self._agents[agent.agent_id] = agent
            self._capability_map[agent.agent_id] = capabilities
            self.logger.info(f"Registered agent {agent.agent_id} with capabilities: {capabilities}")
            
            # Notify capability change
            try:
                await self._workflow_notifier.notify_capability_change(agent.agent_id, capabilities)
            except Exception as e:
                self.logger.error(f"Failed to notify capability change: {e}")
                raise
                
        print(f"[DEBUG] After registration - _agents: {self._agents}")
        
        # Notify observers
        for observer in self._observers:
            try:
                await observer.on_agent_registered(agent.agent_id)
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
                    await observer.on_agent_unregistered(agent_id)
                except Exception as e:
                    self.logger.error(f"Error notifying observer of agent unregistration: {e}")
    
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
            
        capabilities = await self.get_agent_capabilities(agent_id)
        return {
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type,
            "capabilities": list(capabilities),  # Convert set to list
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

    async def recover_agent(self, agent_id: str) -> bool:
        """Recover an agent from error state."""
        async with self._agent_locks[agent_id]:
            agent = self._agents.get(agent_id)
            if not agent:
                self.logger.warning(f"Agent {agent_id} not found")
                return False
            try:
                # Get current state from knowledge graph
                current_state = await agent.query_knowledge_graph({
                    "sparql": f"""
                        SELECT ?status ?recovery_attempts WHERE {{
                            <http://example.org/agent/{agent_id}> <http://example.org/agent/hasStatus> ?status ;
                                             <http://example.org/agent/hasRecoveryAttempts> ?recovery_attempts .
                        }}
                    """
                })
                # Check if recovery is possible
                if current_state and int(current_state[0].get("recovery_attempts", "0")) >= agent.max_recovery_attempts:
                    self.logger.warning(f"Agent {agent_id} has exceeded max recovery attempts")
                    # Ensure KG is updated even if max attempts exceeded
                    triple_fail = {
                        f"http://example.org/agent/{agent_id}": {
                            "http://example.org/agent/hasStatus": "http://example.org/agent/error",
                            "http://example.org/agent/hasRecoveryAttempts": str(agent.recovery_attempts),
                            "http://example.org/agent/lastRecoveryTime": datetime.utcnow().isoformat()
                        }
                    }
                    await agent.update_knowledge_graph(triple_fail)
                    self.logger.debug(f"[DEBUG] KG triple written (max attempts): subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasStatus, object=http://example.org/agent/error")
                    self.logger.debug(f"[DEBUG] KG triple written (max attempts): subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasRecoveryAttempts, object={agent.recovery_attempts}")
                    await self.notify_agent_recovery(agent_id, False)
                    return False

                # Attempt recovery with timeout handling
                import time
                start_time = time.time()
                try:
                    # Set a timeout for recovery if specified
                    recovery_timeout = getattr(agent, 'recovery_timeout', 2.0)
                    success = await asyncio.wait_for(agent.recover(), timeout=recovery_timeout)
                except asyncio.TimeoutError:
                    self.logger.error(f"[DEBUG] Recovery timeout for {agent_id}")
                    agent.status = AgentStatus.ERROR
                    agent.recovery_attempts += 1
                    triple_timeout = {
                        f"http://example.org/agent/{agent_id}": {
                            "http://example.org/agent/hasStatus": "http://example.org/agent/error",
                            "http://example.org/agent/hasRecoveryAttempts": str(agent.recovery_attempts),
                            "http://example.org/agent/lastRecoveryTime": datetime.utcnow().isoformat()
                        }
                    }
                    await agent.update_knowledge_graph(triple_timeout)
                    self.logger.debug(f"[DEBUG] KG triple written (timeout): subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasStatus, object=http://example.org/agent/error")
                    self.logger.debug(f"[DEBUG] KG triple written (timeout): subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasRecoveryAttempts, object={agent.recovery_attempts}")
                    await self.notify_agent_recovery(agent_id, False)
                    return False
                except asyncio.CancelledError:
                    self.logger.error(f"[DEBUG] Recovery cancelled for {agent_id}")
                    agent.status = AgentStatus.ERROR
                    agent.recovery_attempts += 1
                    triple_cancelled = {
                        f"http://example.org/agent/{agent_id}": {
                            "http://example.org/agent/hasStatus": "http://example.org/agent/error",
                            "http://example.org/agent/hasRecoveryAttempts": str(agent.recovery_attempts),
                            "http://example.org/agent/lastRecoveryTime": datetime.utcnow().isoformat()
                        }
                    }
                    await agent.update_knowledge_graph(triple_cancelled)
                    self.logger.debug(f"[DEBUG] KG triple written (cancelled): subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasStatus, object=http://example.org/agent/error")
                    self.logger.debug(f"[DEBUG] KG triple written (cancelled): subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasRecoveryAttempts, object={agent.recovery_attempts}")
                    await self.notify_agent_recovery(agent_id, False)
                    return False

                recovery_time = time.time() - start_time
                metric_node = f"http://example.org/agent/{agent_id}_recovery_metric"
                # Step 1: Update metric node for recovery attempts and time
                triple_metric = {
                    f"http://example.org/agent/{agent_id}": {
                        "http://example.org/agent/hasMetric": metric_node
                    },
                    metric_node: {
                        "http://example.org/agent/hasMetricValue": str(agent.recovery_attempts),
                        "http://example.org/agent/recoveryTime": str(recovery_time)
                    }
                }
                await agent.update_knowledge_graph(triple_metric)
                self.logger.debug(f"[DEBUG] KG triple written: subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasMetric, object={metric_node}")
                self.logger.debug(f"[DEBUG] KG triple written: subject={metric_node}, predicate=http://example.org/agent/hasMetricValue, object={agent.recovery_attempts}")
                self.logger.debug(f"[DEBUG] KG triple written: subject={metric_node}, predicate=http://example.org/agent/recoveryTime, object={recovery_time}")
                if success:
                    # Update knowledge graph with new state
                    agent.status = AgentStatus.IDLE
                    triple_success = {
                        f"http://example.org/agent/{agent_id}": {
                            "http://example.org/agent/hasStatus": "http://example.org/agent/idle",
                            "http://example.org/agent/hasRecoveryAttempts": str(agent.recovery_attempts),
                            "http://example.org/agent/lastRecoveryTime": datetime.utcnow().isoformat()
                        }
                    }
                    await agent.update_knowledge_graph(triple_success)
                    self.logger.debug(f"[DEBUG] KG triple written: subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasStatus, object=http://example.org/agent/idle")
                    self.logger.debug(f"[DEBUG] KG triple written: subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasRecoveryAttempts, object={agent.recovery_attempts}")
                    await self.notify_agent_recovery(agent_id, True)
                    self.logger.info(f"Successfully recovered agent {agent_id}")
                else:
                    # Update knowledge graph with failure state
                    agent.status = AgentStatus.ERROR
                    triple_fail = {
                        f"http://example.org/agent/{agent_id}": {
                            "http://example.org/agent/hasStatus": "http://example.org/agent/error",
                            "http://example.org/agent/hasRecoveryAttempts": str(agent.recovery_attempts),
                            "http://example.org/agent/lastRecoveryTime": datetime.utcnow().isoformat()
                        }
                    }
                    await agent.update_knowledge_graph(triple_fail)
                    self.logger.debug(f"[DEBUG] KG triple written: subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasStatus, object=http://example.org/agent/error")
                    self.logger.debug(f"[DEBUG] KG triple written: subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasRecoveryAttempts, object={agent.recovery_attempts}")
                    await self.notify_agent_recovery(agent_id, False)
                    self.logger.warning(f"Failed to recover agent {agent_id}")
                return success
            except Exception as e:
                self.logger.error(f"Error during agent recovery: {e}")
                # Ensure KG is updated on error
                agent.status = AgentStatus.ERROR
                agent.recovery_attempts += 1
                triple_error = {
                    f"http://example.org/agent/{agent_id}": {
                        "http://example.org/agent/hasStatus": "http://example.org/agent/error",
                        "http://example.org/agent/hasRecoveryAttempts": str(agent.recovery_attempts),
                        "http://example.org/agent/lastRecoveryTime": datetime.utcnow().isoformat()
                    }
                }
                await agent.update_knowledge_graph(triple_error)
                self.logger.debug(f"[DEBUG] KG triple written (exception): subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasStatus, object=http://example.org/agent/error")
                self.logger.debug(f"[DEBUG] KG triple written (exception): subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasRecoveryAttempts, object={agent.recovery_attempts}")
                await self.notify_agent_recovery(agent_id, False)
                return False

    async def update_agent_status(self, agent_id: str, status: str) -> None:
        """Update agent status and notify observers."""
        async with self._agent_locks[agent_id]:
            agent = self._agents.get(agent_id)
            if not agent:
                self.logger.warning(f"Agent {agent_id} not found")
                return
            try:
                # Step 1: Update local state
                agent.status = status
                self.logger.debug(f"[DEBUG] Local status updated for {agent_id}: {status}")
                # Step 2: Update knowledge graph with status
                triple_status = {
                    f"http://example.org/agent/{agent_id}": {
                        "http://example.org/agent/hasStatus": f"http://example.org/agent/{status}",
                        "http://example.org/agent/lastStatusUpdate": datetime.utcnow().isoformat()
                    }
                }
                await agent.update_knowledge_graph(triple_status)
                self.logger.debug(f"[DEBUG] KG triple written: subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasStatus, object=http://example.org/agent/{status}")
                # Step 3: If error, increment recovery attempts and update KG
                if status == "error":
                    agent.recovery_attempts += 1
                    self.logger.debug(f"[DEBUG] Recovery attempts incremented for {agent_id}: {agent.recovery_attempts}")
                    triple_attempts = {
                        f"http://example.org/agent/{agent_id}": {
                            "http://example.org/agent/hasRecoveryAttempts": str(agent.recovery_attempts),
                            "http://example.org/agent/lastErrorTime": datetime.utcnow().isoformat()
                        }
                    }
                    await agent.update_knowledge_graph(triple_attempts)
                    self.logger.debug(f"[DEBUG] KG triple written: subject=http://example.org/agent/{agent_id}, predicate=http://example.org/agent/hasRecoveryAttempts, object={agent.recovery_attempts}")
                    # Step 4: Attempt recovery if within limits
                    if agent.recovery_attempts < agent.max_recovery_attempts:
                        await self.recover_agent(agent_id)
                    else:
                        self.logger.warning(f"Agent {agent_id} has exceeded max recovery attempts")
                        await self.notify_agent_recovery(agent_id, False)
                # Step 5: Notify observers
                await self.notify_agent_status(agent_id, status)
                self.logger.debug(f"[DEBUG] Notified observers of status change for {agent_id}: {status}")
            except Exception as e:
                self.logger.error(f"Error updating agent status: {e}")

    async def notify_agent_status(self, agent_id: str, status: str) -> None:
        """Notify observers of agent status change."""
        for observer in self._observers:
            try:
                await observer.on_agent_status_changed(agent_id, status)
            except Exception as e:
                self.logger.error(f"Error notifying observer of agent status change: {e}")
                
    async def notify_agent_recovery(self, agent_id: str, success: bool) -> None:
        """Notify observers of agent recovery attempt."""
        for observer in self._observers:
            try:
                if success:
                    await observer.on_agent_recovered(agent_id)
                else:
                    await observer.on_agent_recovery_failed(agent_id)
            except Exception as e:
                self.logger.error(f"Error notifying observer of agent recovery: {e}") 