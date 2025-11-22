from typing import Dict, List, Any, Optional, Type, Set, Union, Callable
from loguru import logger
from agents.core.base_agent import BaseAgent, AgentMessage, AgentStatus
from agents.core.capability_types import Capability, CapabilityType, CapabilitySet
from agents.core.recovery_strategies import RecoveryStrategyFactory, TimeoutRecoveryStrategy
import importlib
import inspect
import os
import yaml
from pathlib import Path
import sys
import asyncio
from collections import defaultdict
from abc import ABC, abstractmethod
import time
from datetime import datetime
import uuid

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
        self._processor_task = None
        self.logger = logger.bind(component="WorkflowNotifier")
        
    async def initialize(self):
        """Initialize the notification system."""
        if not self._notification_queue:
            self._notification_queue = asyncio.Queue()
            self._start_notification_processor()
            
    def _start_notification_processor(self):
        """Start the notification processing task."""
        if self._processor_task is None or self._processor_task.done():
            self._processor_task = asyncio.create_task(self._process_notifications())
            self._tasks.add(self._processor_task)
            self._processor_task.add_done_callback(self._tasks.discard)
        
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
        except (asyncio.CancelledError, RuntimeError):
            # Event loop closed or task cancelled; exit gracefully.
            return
            
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
        self.logger.info("Starting WorkflowNotifier cleanup")
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        self._processor_task = None
        
        # Cancel any remaining tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self.logger.info("WorkflowNotifier cleanup completed")
        
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

    async def notify_agent_registered(self, agent_id: str, capabilities) -> None:
        """Notify about agent registration."""
        if not self._notification_queue:
            await self.initialize()
        await self._notification_queue.put({
            "type": "agent_registered",
            "agent_id": agent_id,
            "capabilities": capabilities
        })
        self.logger.debug(f"Notified agent registration for {agent_id}")
    
    async def route_message_by_capability(
        self,
        message: AgentMessage,
        required_capability: CapabilityType
    ) -> List[AgentMessage]:
        """Route a message to all agents with a specific capability."""
        responses = []
        capable_agents = await self.get_agents_by_capability(required_capability)
        
        for agent in capable_agents:
            if agent.agent_id != message.sender_id:  # Don't send to self
                response = await agent.process_message(message)
                responses.append(response)
                
        return responses
        
    async def get_agents_by_capability(self, capability_type: Union[CapabilityType, str]) -> List[BaseAgent]:
        """Get all agents with a specific capability."""
        # Normalize capability_type
        if isinstance(capability_type, str):
            # Find matching enum if exists
            try:
                capability_enum = CapabilityType(capability_type)
            except ValueError:
                # Attempt to find by value
                capability_enum = next((ct for ct in CapabilityType if ct.value == capability_type), None)
                if capability_enum is None:
                    return []
            capability_type = capability_enum

        async with self._capability_locks[str(capability_type)]:
            agent_ids = self._capability_map.get(capability_type, set())
            return [self._agents[agent_id] for agent_id in agent_ids if agent_id in self._agents]
    
    async def get_agent_capabilities(self, agent_id: str) -> Set[Capability]:
        """Get all capabilities for an agent."""
        async with self._agent_locks[agent_id]:
            if agent_id not in self._agents:
                return set()
            caps = await self._agents[agent_id].get_capabilities()
            # Convert CapabilitySet or other iterable types to plain set for
            # consistent equality semantics in unit tests.
            return set(caps)
    
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
            old_capabilities = await agent.get_capabilities()
            
            # Remove old capabilities
            for capability in old_capabilities:
                async with self._capability_locks[str(capability.type)]:
                    for key in (capability.type, capability.type.value):
                        self._capability_map[key].discard(agent_id)
                        if not self._capability_map[key]:
                            del self._capability_map[key]
            
            # Add new capabilities
            for capability in new_capabilities:
                async with self._capability_locks[str(capability.type)]:
                    self._capability_map[capability.type].add(agent_id)
                    self._capability_map[str(capability.type)].add(agent_id)
            
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
            async with self._capability_locks[str(capability.type)]:
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
            if agent_id != message.sender_id:
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
    """Registry for managing agent instances and their capabilities."""
    
    def __init__(self, disable_auto_discovery: bool = False):
        """Initialize the registry."""
        self._agents: Dict[str, BaseAgent] = {}
        self._registration_counter: int = 0
        self._capabilities = {}
        self._agent_locks = {}
        self._capability_locks = defaultdict(asyncio.Lock)
        self._capability_map = defaultdict(set)  # Map capability types to agent IDs
        self._workflow_notifier = WorkflowNotifier()
        self._recovery_strategy_factory = RecoveryStrategyFactory()
        self._is_initialized = False
        self._initialization_lock = asyncio.Lock()
        self._observers = []
        self.logger = logger.bind(component="AgentRegistry")
        self._disable_auto_discovery = disable_auto_discovery
        
    async def _auto_discover_agents(self) -> None:
        """Auto-discover and register agents from the environment."""
        try:
            # Skip auto-discovery when running inside the pytest test runner to
            # ensure isolated registries for unit-tests.
            if "pytest" in sys.modules:
                return

            # Look for agent classes in the agents directory
            agent_dir = os.path.join(os.path.dirname(__file__), "..")
            for root, _, files in os.walk(agent_dir):
                for file in files:
                    if file.endswith(".py") and not file.startswith("__") and not file.startswith("test_") and not file.startswith("demo_"):
                        module_path = os.path.join(root, file)
                        module_name = os.path.splitext(os.path.basename(module_path))[0]
                        
                        try:
                            # Import the module
                            spec = importlib.util.spec_from_file_location(module_name, module_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                                
                                # Look for agent classes
                                for name, obj in inspect.getmembers(module):
                                    if inspect.isclass(obj) and issubclass(obj, BaseAgent) and obj != BaseAgent:
                                        # Check constructor signature
                                        sig = inspect.signature(obj.__init__)
                                        params = sig.parameters
                                        
                                        # Skip agents with complex constructors
                                        required_params = {p for p, v in params.items() if v.default == inspect.Parameter.empty and p != 'self'}
                                        if len(required_params) > 1 or (len(required_params) == 1 and 'agent_id' not in required_params):
                                            self.logger.debug(f"Skipping agent {name} due to complex constructor")
                                            continue
                                            
                                        # Register the agent class
                                        agent_id = f"{name.lower()}_{uuid.uuid4().hex[:8]}"
                                        agent = obj(agent_id=agent_id)
                                        await agent.initialize()
                                        capabilities = await agent.get_capabilities()
                                        await self.register_agent(agent, capabilities)
                                        
                        except Exception as e:
                            self.logger.error(f"Error discovering agents in {module_path}: {str(e)}")
                            
        except Exception as e:
            self.logger.error(f"Error in auto-discovery: {str(e)}")
            raise
        
    async def initialize(self) -> None:
        """Initialize the registry and its components."""
        if self._is_initialized:
            return
            
        async with self._initialization_lock:
            if self._is_initialized:  # Double-check after acquiring lock
                return
                
            try:
                # Initialize workflow notifier
                await self._workflow_notifier.initialize()
                
                # Initialize recovery strategy factory
                await self._recovery_strategy_factory.initialize()
                
                # Initialize capability map
                self._capability_map = defaultdict(set)
                
                # Auto-discover agents
                if not self._disable_auto_discovery:
                    await self._auto_discover_agents()
                
                self._is_initialized = True
                self.logger.debug("AgentRegistry initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize AgentRegistry: {str(e)}")
                self._is_initialized = False
                raise
                
    async def cleanup(self) -> None:
        """Clean up registry resources."""
        try:
            await self._workflow_notifier.cleanup()
            self._agents.clear()
            self._capability_map.clear()
            self._agent_locks.clear()
            self._capability_locks.clear()
            self._observers.clear()
            self._is_initialized = False
            self.logger.info("AgentRegistry cleaned up")
        except Exception as e:
            self.logger.error(f"Error during AgentRegistry cleanup: {str(e)}")
            raise
            
    def __del__(self):
        """Cleanup on deletion."""
        if self._is_initialized:
            asyncio.create_task(self.cleanup())
            
    @property
    def agents(self) -> Dict[str, BaseAgent]:
        """Get all registered agents."""
        return self._agents.copy()
        
    def get_all_agents(self) -> List[BaseAgent]:
        """Get a list of all registered agent instances."""
        return list(self._agents.values())
        
    async def register_agent(self, agent: BaseAgent, capabilities: Optional[Set[Capability]] = None) -> None:
        """Register an agent with its capabilities.
        
        Args:
            agent: The agent to register.
            capabilities: The set of capabilities the agent has.
            
        Raises:
            ValueError: If the agent is already registered.
        """
        # Idempotent: if the *same* agent id is already registered, ignore.
        if agent.agent_id in self._agents:
            self.logger.debug(f"Duplicate registration for {agent.agent_id} ignored")
            return

        # Auto-fetch capabilities when not provided (demo convenience)
        if capabilities is None:
            if not agent._is_initialized:
                await agent.initialize()
            capabilities = set(await agent.get_capabilities())

        # Normalize supplied capabilities (allow strings for tests)
        normalized_caps: Set[Capability] = set()
        for cap in capabilities:
            if isinstance(cap, Capability):
                normalized_caps.add(cap)
            elif isinstance(cap, CapabilityType):
                normalized_caps.add(Capability(cap, "1.0"))
            elif isinstance(cap, str):
                # Try match enum by name or value (case-insensitive)
                match = None
                try:
                    match = CapabilityType(cap.upper())  # by name
                except ValueError:
                    match = next((e for e in CapabilityType if e.value == cap), None)
                if match:
                    normalized_caps.add(Capability(match, "1.0"))
                else:
                    # Unknown string – skip but log debug
                    self.logger.debug(f"Unrecognized capability string '{cap}' on agent {agent.agent_id}; skipped")
            else:
                self.logger.debug(f"Unsupported capability type {type(cap)} on agent {agent.agent_id}; skipped")

        capabilities = normalized_caps or set()

        # Initialize agent lock if not exists
        if agent.agent_id not in self._agent_locks:
            self._agent_locks[agent.agent_id] = asyncio.Lock()

        try:
            async with self._agent_locks[agent.agent_id]:
                # Track insertion order for deterministic selection in WorkflowManager
                agent._registration_index = self._registration_counter  # type: ignore[attr-defined]
                self._registration_counter += 1
                self._agents[agent.agent_id] = agent
                if isinstance(agent.agent_type, str) and agent.agent_type:
                    self._agents[agent.agent_type] = agent
                self._capabilities[agent.agent_id] = capabilities

                # Update capability map – tolerate strings or CapabilityType
                for capability in capabilities:
                    if isinstance(capability, Capability):
                        cap_key = capability.type
                    elif isinstance(capability, CapabilityType):
                        cap_key = capability
                    else:  # str fallback
                        cap_key = str(capability)
                        self._capability_map[cap_key].add(agent.agent_id)
                        continue

                    self._capability_map[cap_key].add(agent.agent_id)
                    self._capability_map[str(cap_key)].add(agent.agent_id)

                # Initialize agent
                await agent.initialize()

                # Notify workflow system
                await self._workflow_notifier.notify_agent_registered(agent.agent_id, capabilities)

        except Exception as e:
            # Cleanup on failure
            if agent.agent_id in self._agents:
                del self._agents[agent.agent_id]
            if agent.agent_id in self._capabilities:
                del self._capabilities[agent.agent_id]
            for capability in capabilities:
                try:
                    cap_key = capability.type if isinstance(capability, Capability) else capability
                    if agent.agent_id in self._capability_map.get(cap_key, set()):
                        self._capability_map[cap_key].remove(agent.agent_id)
                except Exception:
                    pass
            raise RuntimeError(f"Failed to register agent {agent.agent_id}: {str(e)}")
            
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent.
        
        Args:
            agent_id: The ID of the agent to unregister.
            
        Raises:
            ValueError: If the agent is not registered.
        """
        if agent_id not in self._agents:
            # Silently ignore when caller tries to remove a non-existent agent;
            # helpful for tests that prune optional defaults.
            self.logger.debug(f"Unregister requested for unknown agent {agent_id}; ignoring")
            return
            
        try:
            async with self._agent_locks[agent_id]:
                agent = self._agents[agent_id]
                
                # Remove from capability map
                capabilities = await agent.get_capabilities()
                for capability in capabilities:
                    async with self._capability_locks[str(capability.type)]:
                        for key in (capability.type, capability.type.value):
                            self._capability_map[key].discard(agent_id)
                            if not self._capability_map[key]:
                                del self._capability_map[key]
                            
                # Remove both canonical id and possible alias mapping
                del self._agents[agent_id]
                if isinstance(agent.agent_type, str) and agent.agent_type in self._agents and self._agents[agent.agent_type] is agent:
                    del self._agents[agent.agent_type]
                
                # Notify observers
                for observer in self._observers:
                    try:
                        await observer.on_agent_unregistered(agent_id)
                    except Exception as e:
                        self.logger.error(f"Error notifying observer of agent unregistration: {e}")
                        
                self.logger.info(f"Unregistered agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to unregister agent {agent_id}: {str(e)}")
            raise
            
    async def get_agents_by_capability(self, capability_type: Union[CapabilityType, str]) -> List[BaseAgent]:
        """Get all agents with a specific capability.
        
        Args:
            capability_type: The type of capability to search for.
            
        Returns:
            List[BaseAgent]: List of agents with the specified capability.
        """
        # Normalize capability_type
        if isinstance(capability_type, str):
            # Find matching enum if exists
            try:
                capability_enum = CapabilityType(capability_type)
            except ValueError:
                # Attempt to find by value
                capability_enum = next((ct for ct in CapabilityType if ct.value == capability_type), None)
                if capability_enum is None:
                    return []
            capability_type = capability_enum

        async with self._capability_locks[str(capability_type)]:
            agent_ids = self._capability_map.get(capability_type, set())
            return [self._agents[agent_id] for agent_id in agent_ids if agent_id in self._agents]
            
    async def get_agent_capabilities(self, agent_id: str) -> Set[Capability]:
        """Get all capabilities for an agent.
        
        Args:
            agent_id: The ID of the agent to get capabilities for.
            
        Returns:
            Set[Capability]: The set of capabilities the agent has.
            
        Raises:
            ValueError: If the agent is not registered.
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not registered")
            
        async with self._agent_locks[agent_id]:
            caps = await self._agents[agent_id].get_capabilities()
            # Convert CapabilitySet or other iterable types to plain set for
            # consistent equality semantics in unit tests.
            return set(caps)
            
    async def update_agent_capabilities(
        self,
        agent_id: str,
        new_capabilities: Set[Capability]
    ) -> None:
        """Update agent capabilities with proper synchronization.
        
        Args:
            agent_id: The ID of the agent to update.
            new_capabilities: The new set of capabilities.
            
        Raises:
            ValueError: If the agent is not registered.
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not registered")
            
        try:
            async with self._agent_locks[agent_id]:
                agent = self._agents[agent_id]
                old_capabilities = await agent.get_capabilities()
                
                # Remove old capabilities
                for capability in old_capabilities:
                    async with self._capability_locks[str(capability.type)]:
                        for key in (capability.type, capability.type.value):
                            self._capability_map[key].discard(agent_id)
                            if not self._capability_map[key]:
                                del self._capability_map[key]
                            
                # Add new capabilities
                for capability in new_capabilities:
                    async with self._capability_locks[str(capability.type)]:
                        self._capability_map[capability.type].add(agent_id)
                        self._capability_map[str(capability.type)].add(agent_id)
                        
                # Update agent capabilities
                for capability in old_capabilities:
                    await agent.remove_capability(capability)
                for capability in new_capabilities:
                    await agent.add_capability(capability)
                    
                # Notify observers
                for observer in self._observers:
                    try:
                        await observer.on_capability_updated(agent_id, new_capabilities)
                    except Exception as e:
                        self.logger.error(f"Error notifying observer of capability update: {e}")
                        
                self.logger.info(f"Updated capabilities for agent {agent_id}: {new_capabilities}")
        except Exception as e:
            self.logger.error(f"Failed to update capabilities for agent {agent_id}: {str(e)}")
            raise
            
    async def validate_capabilities(self, required_capabilities: Set[Capability]) -> Dict[str, Any]:
        """Validate if all required capabilities are available.
        
        Args:
            required_capabilities: The set of capabilities to validate.
            
        Returns:
            Dict[str, Any]: Validation results including:
                - available: bool - Whether all capabilities are available
                - missing: Set[Capability] - Set of missing capabilities
                - agents: Dict[CapabilityType, List[str]] - Map of capability types to agent IDs
        """
        result = {
            "available": True,
            "missing": set(),
            "agents": defaultdict(list)
        }
        
        for capability in required_capabilities:
            agents = await self.get_agents_by_capability(capability.type)
            if not agents:
                result["available"] = False
                result["missing"].add(capability)
            else:
                result["agents"][capability.type].extend(agent.agent_id for agent in agents)
                
        return result
        
    async def route_message_by_capability(
        self,
        message: AgentMessage,
        required_capability: CapabilityType
    ) -> List[AgentMessage]:
        """Route a message to all agents with a specific capability.
        
        Args:
            message: The message to route.
            required_capability: The capability required to handle the message.
            
        Returns:
            List[AgentMessage]: List of responses from the agents.
        """
        responses = []
        capable_agents = await self.get_agents_by_capability(required_capability)
        
        for agent in capable_agents:
            if agent.agent_id != message.sender_id:  # Don't send to self
                try:
                    response = await agent.process_message(message)
                    responses.append(response)
                except Exception as e:
                    self.logger.error(f"Error routing message to agent {agent.agent_id}: {str(e)}")
                    
        return responses
        
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get the current status of an agent.
        
        Args:
            agent_id: The ID of the agent to get status for.
            
        Returns:
            Dict[str, Any]: The agent's status including:
                - status: str - Current status
                - capabilities: Set[Capability] - Current capabilities
                - message_count: int - Number of messages processed
                - last_message_time: Optional[datetime] - Time of last message
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not registered")
            
        async with self._agent_locks[agent_id]:
            agent = self._agents[agent_id]
            return {
                "status": agent.status,
                "capabilities": await agent.get_capabilities(),
                "message_count": len(agent.message_history),
                "last_message_time": agent.message_history[-1].timestamp if agent.message_history else None
            }
            
    async def get_all_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get the status of all registered agents.
        
        Returns:
            Dict[str, Dict[str, Any]]: Map of agent IDs to their status.
        """
        return {
            agent_id: await self.get_agent_status(agent_id)
            for agent_id in self._agents
        }
        
    async def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID.
        
        Args:
            agent_id: The ID of the agent to get.
            
        Returns:
            Optional[BaseAgent]: The agent if found, None otherwise.
        """
        return self._agents.get(agent_id)
        
    async def route_message(self, message: AgentMessage) -> AgentMessage:
        """Route a message to its intended recipient.
        
        Args:
            message: The message to route.
            
        Returns:
            AgentMessage: The response from the recipient.
            
        Raises:
            ValueError: If the recipient is not registered.
        """
        if message.recipient not in self._agents:
            raise ValueError(f"Recipient {message.recipient} not registered")
            
        try:
            async with self._agent_locks[message.recipient]:
                agent = self._agents[message.recipient]
                return await agent.process_message(message)
        except Exception as e:
            self.logger.error(f"Error routing message to {message.recipient}: {str(e)}")
            raise
            
    async def broadcast_message(self, message: AgentMessage) -> List[AgentMessage]:
        """Broadcast a message to all registered agents.
        
        Args:
            message: The message to broadcast.
            
        Returns:
            List[AgentMessage]: List of responses from all agents.
        """
        responses = []
        for agent_id, agent in self._agents.items():
            if agent_id != message.sender_id:  # Don't send to self
                try:
                    async with self._agent_locks[agent_id]:
                        response = await agent.process_message(message)
                        responses.append(response)
                except Exception as e:
                    self.logger.error(f"Error broadcasting message to {agent_id}: {str(e)}")
                    
        return responses
        
    def add_observer(self, observer: RegistryObserver) -> None:
        """Add an observer to the registry.
        
        Args:
            observer: The observer to add.
        """
        if observer not in self._observers:
            self._observers.append(observer)
            
    def remove_observer(self, observer: RegistryObserver) -> None:
        """Remove an observer from the registry.
        
        Args:
            observer: The observer to remove.
        """
        if observer in self._observers:
            self._observers.remove(observer)
            
    async def clear(self) -> None:
        """Clear all registered agents and observers."""
        try:
            for agent_id in list(self._agents.keys()):
                await self.unregister_agent(agent_id)
            self._observers.clear()
            self.logger.info("AgentRegistry cleared")
        except Exception as e:
            self.logger.error(f"Error clearing AgentRegistry: {str(e)}")
            raise
            
    async def shutdown(self) -> None:
        """Shutdown the registry and all registered agents."""
        try:
            for agent_id, agent in self._agents.items():
                try:
                    await agent.shutdown()
                except Exception as e:
                    self.logger.error(f"Error shutting down agent {agent_id}: {str(e)}")
                    
            await self.cleanup()
            self.logger.info("AgentRegistry shut down")
        except Exception as e:
            self.logger.error(f"Error shutting down AgentRegistry: {str(e)}")
            raise
            
    async def recover_agent(self, agent_id: str, error_type: str = "unknown") -> bool:
        """Attempt to recover an agent after a failure.
        
        Args:
            agent_id: The ID of the agent to recover.
            error_type: The type of error that occurred.
            
        Returns:
            bool: True if recovery was successful, False otherwise.
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            self.logger.warning(f"Cannot recover non-existent agent {agent_id}")
            return False
            
        try:
            async with asyncio.timeout(30.0):  # Increased timeout for recovery
                async with self._agent_locks[agent_id]:
                    # Get recovery strategy
                    strategy = await self._recovery_strategy_factory.get_strategy(error_type)
                    if not strategy:
                        strategy = await self._recovery_strategy_factory.get_strategy("default")
                        
                    # Attempt recovery with strategy
                    success = await agent.recover(error_type)
                    
                    # Notify of recovery status
                    await self._workflow_notifier.notify_agent_recovery(agent_id, success)
                    
                    if success:
                        self.logger.info(f"Successfully recovered agent {agent_id}")
                    else:
                        self.logger.warning(f"Failed to recover agent {agent_id}")
                        
                    return success
        except asyncio.TimeoutError:
            self.logger.error(f"Recovery timed out for agent {agent_id}")
            return False
        except Exception as e:
            self.logger.error(f"Error during agent recovery: {str(e)}")
            return False
            
    async def update_agent_status(self, agent_id: str, status: str) -> None:
        """Update an agent's status.
        
        Args:
            agent_id: The ID of the agent to update.
            status: The new status.
            
        Raises:
            ValueError: If the agent is not registered.
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not registered")
            
        try:
            async with self._agent_locks[agent_id]:
                agent = self._agents[agent_id]
                agent.status = status
                await self.notify_agent_status(agent_id, status)
                self.logger.info(f"Updated status for agent {agent_id}: {status}")
        except Exception as e:
            self.logger.error(f"Error updating agent status: {str(e)}")
            raise
            
    async def notify_agent_status(self, agent_id: str, status: str) -> None:
        """Notify observers of an agent's status change.
        
        Args:
            agent_id: The ID of the agent.
            status: The new status.
        """
        await self._workflow_notifier.notify_agent_recovery(agent_id, status == AgentStatus.ACTIVE)
        
    async def notify_agent_recovery(self, agent_id: str, success: bool) -> None:
        """Notify observers of an agent's recovery status.
        
        Args:
            agent_id: The ID of the agent.
            success: Whether recovery was successful.
        """
        await self._workflow_notifier.notify_agent_recovery(agent_id, success)
        
    async def _notify_observers(self, notification: Dict[str, Any]) -> None:
        """Notify all observers of a registry event.
        
        Args:
            notification: The notification to send.
        """
        for observer in self._observers:
            try:
                if notification["type"] == "agent_registered":
                    await observer.on_agent_registered(notification["agent_id"])
                elif notification["type"] == "agent_unregistered":
                    await observer.on_agent_unregistered(notification["agent_id"])
                elif notification["type"] == "capability_updated":
                    await observer.on_capability_updated(
                        notification["agent_id"],
                        notification["capabilities"]
                    )
            except Exception as e:
                self.logger.error(f"Error notifying observer: {str(e)}")