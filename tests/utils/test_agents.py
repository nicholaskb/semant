from typing import Dict, Any, List, Optional, Set, Union
from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
import time
from datetime import datetime
from agents.core.capability_types import Capability, CapabilityType
from agents.core.workflow_types import Workflow

class BaseTestAgent(BaseAgent):
    """Base test agent with async capabilities."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "test",
        capabilities: Optional[Set[Capability]] = None,
        config: Optional[Dict[str, Any]] = None,
        default_response: Optional[Dict] = None,
        knowledge_graph: Optional[KnowledgeGraphManager] = None
    ):
        """Initialize base test agent."""
        # Use caller-provided capabilities as-is when supplied
        super().__init__(agent_id, agent_type, capabilities, config)
        self._default_response = default_response or {"status": "processed"}
        self._message_history = []
        self._knowledge_graph_updates = []
        self._knowledge_graph_queries = []
        self._knowledge_graph = knowledge_graph
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        if not self._is_initialized:
            await super().initialize()
            self._is_initialized = True
            
    async def get_capabilities(self) -> Set[Capability]:
        """Get agent capabilities."""
        if not self._is_initialized:
            await self.initialize()
        # Convert CapabilitySet to plain set for test equality
        return set(self._capabilities)
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process a message asynchronously."""
        if not self._is_initialized:
            await self.initialize()
            
        self._message_history.append({
            "message": message,
            "timestamp": time.time()
        })
        
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=self._default_response,
            timestamp=time.time(),
            message_type="response"
        )
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update knowledge graph asynchronously."""
        if not self._is_initialized:
            await self.initialize()
            
        if self._knowledge_graph:
            await self._knowledge_graph.add_triple(
                subject=update_data.get("subject"),
                predicate=update_data.get("predicate"),
                object=update_data.get("object")
            )
            
        # Always record timestamp so tests can assert chronological ordering
        import time as _t
        self._knowledge_graph_updates.append({"data": update_data, "timestamp": _t.time()})
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query knowledge graph asynchronously."""
        if not self._is_initialized:
            await self.initialize()
            
        # Track queries for test verification
        self._knowledge_graph_queries.append({
            "query": query,
            "timestamp": time.time()
        })
        if self._knowledge_graph and isinstance(query.get("sparql"), str):
            return await self._knowledge_graph.query_graph(query["sparql"])
        return {"result": "test_result"}
        
    def get_message_history(self) -> List[Dict]:
        """Get message history."""
        return self._message_history
        
    def get_knowledge_graph_updates(self) -> List[Dict]:
        """Get knowledge graph updates."""
        return self._knowledge_graph_updates
        
    def get_knowledge_graph_queries(self):
        """Return recorded knowledge graph queries."""
        return self._knowledge_graph_queries
        
    async def cleanup(self) -> None:
        """Clean up agent state."""
        self._message_history.clear()
        self._knowledge_graph_updates.clear()
        self._knowledge_graph_queries.clear()
        self._is_initialized = False
        await super().cleanup()

    # Provide awaitable capabilities property compatible with both direct
    # access (list-like) and `await agent.capabilities` in newer tests.
    class _AwaitableCaps(list):
        """List-like object that is also awaitable.

        Direct use   ➜ behaves like a normal list (supports iteration/index).
        `await obj`  ➜ yields the *live* capability **set** from the owning
                       agent so assertions can compare to registry output.
        """

        def __init__(self, sync_list, async_provider):
            super().__init__(sync_list)
            self._provider = async_provider

        def __await__(self):  # type: ignore[override]
            return self._provider().__await__()

    @property
    def capabilities(self):
        # Return an awaitable list of Capability objects for test flexibility.
        caps = list(self._capabilities) if hasattr(self, "_capabilities") else []
        return BaseTestAgent._AwaitableCaps(caps, self.get_capabilities)

class TestAgent(BaseTestAgent):
    """Base test agent implementation."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "test",
        capabilities: Set[Capability] = None,
        default_response: Dict[str, Any] = None
    ):
        """Initialize test agent."""
        if not capabilities:
            capabilities = {
                Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
                Capability(CapabilityType.TASK_EXECUTION, "1.0"),
            }
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=set(capabilities) if capabilities else capabilities,
            default_response=default_response
        )
        self._initialized = False
        self._message_history = []
        self._knowledge_graph_updates = []
        self._should_fail = False
        self._max_fails = 0
        self._fail_count = 0
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        if not self._initialized:
            await super().initialize()
            self._initialized = True
            
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process a message."""
        if not self._initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        # Support dict messages for unit tests
        if isinstance(message, dict):
            message = AgentMessage(**message)

        # Check if should fail
        if self._should_fail and self._fail_count < self._max_fails:
            self._fail_count += 1
            raise Exception(f"Simulated failure (attempt {self._fail_count})")
            
        # Add message to history
        self._message_history.append(message)
        
        # Return default response
        response_msg = {
            "sender_id": self.agent_id,
            "recipient_id": message.sender_id,
            "content": self._default_response or {"status": "success"},
            "timestamp": datetime.now(),
            "message_type": "response"
        }
        # Wrap dictionary into AgentMessage for consistency with other tests
        return AgentMessage(**response_msg)
        
    async def update_knowledge_graph(self, data: Dict[str, Any]) -> None:
        """Update the knowledge graph with new data."""
        if not self._initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        # Preserve original dict exactly for tests that compare equality.
        import time as _t
        self._knowledge_graph_updates.append({"data": data, "timestamp": _t.time()})
        
    def get_message_history(self) -> List[AgentMessage]:
        """Get message history."""
        return self._message_history
        
    def get_knowledge_graph_updates(self) -> List[Dict]:
        """Get knowledge graph updates."""
        return self._knowledge_graph_updates
        
    async def get_capabilities(self) -> Set[Capability]:
        """Get agent capabilities."""
        return self._capabilities
    
    def set_should_fail(self, should_fail: bool = True, max_fails: int = 1) -> None:
        """Set whether the agent should fail on process_message calls."""
        self._should_fail = should_fail
        self._max_fails = max_fails
        self._fail_count = 0  # Reset fail count

    async def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        if not self._initialized:
            await self.initialize()
            
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": await self.get_capabilities(),
            "message_count": len(self._message_history),
            "knowledge_graph_updates": len(self._knowledge_graph_updates)
        }

    # Expose capabilities attribute that is also awaitable
    @property
    def capabilities(self):  # type: ignore[override]
        return BaseTestAgent._AwaitableCaps(list(self._capabilities), self.get_capabilities)

class TestCapabilityAgent(TestAgent):
    """Test agent with capability management."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "capability",
        capabilities: Optional[Set[Capability]] = None,
        config: Optional[Dict[str, Any]] = None,
        default_response: Optional[Dict[str, Any]] = None,
        knowledge_graph: Optional[KnowledgeGraphManager] = None
    ):
        default_capabilities = {
            Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
            Capability(CapabilityType.TASK_EXECUTION, "1.0"),
            Capability(CapabilityType.CAPABILITY_MANAGEMENT, "1.0"),
            Capability(CapabilityType.MONITORING, "1.0"),
            Capability(CapabilityType.SUPERVISION, "1.0")
        }
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=set(capabilities) if capabilities else capabilities,
            default_response=default_response
        )
        self._capability_requests: List[Dict[str, Any]] = []
        self._capability_history: List[Dict[str, Any]] = []
        
    async def request_capability(self, capability: Capability) -> bool:
        """Request a new capability."""
        if not self._initialized:
            await self.initialize()
            
        request = {
            "capability": capability,
            "timestamp": time.time(),
            "status": "pending"
        }
        self._capability_requests.append(request)
        self._capability_history.append(request)
        
        # Return success
        return True
        
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get pending capability requests."""
        return [r for r in self._capability_requests if r["status"] == "pending"]
        
    async def get_capability_requests(self) -> List[Capability]:
        """Get capability requests - compatibility method for tests."""
        pending = self.get_pending_requests()
        return [request["capability"] for request in pending]
        
    def get_capability_history(self) -> List[Dict[str, Any]]:
        """Get capability request history."""
        return self._capability_history
        
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        status = await super().get_status()
        status.update({
            "pending_requests": len(self.get_pending_requests()),
            "total_requests": len(self._capability_history)
        })
        return status
        
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        self._capability_requests.clear()
        self._capability_history.clear()
        await super().cleanup()

class MockAgent(BaseTestAgent):
    """Mock agent for testing."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "mock",
        capabilities: Optional[Set[Capability]] = None,
        config: Optional[Dict[str, Any]] = None,
        default_response: Optional[Dict[str, Any]] = None,
        knowledge_graph: Optional[KnowledgeGraphManager] = None
    ):
        # If caller did not supply capabilities, fall back to sensible defaults
        if capabilities is None:
            capabilities = {
                Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
                Capability(CapabilityType.TASK_EXECUTION, "1.0"),
                Capability(CapabilityType.SENSOR_DATA, "1.0"),
                Capability(CapabilityType.TEST_SENSOR, "1.0"),
            }

        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            config=config,
            default_response=default_response,
            knowledge_graph=knowledge_graph
        )
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        if not self._is_initialized:
            await super().initialize()
            self._is_initialized = True
            
    async def get_capabilities(self) -> Set[Capability]:
        """Get agent capabilities as a plain set for equality checks."""
        return await super().get_capabilities()
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message."""
        if not self._is_initialized:
            await self.initialize()
            
        self._message_history.append(message)
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=self._default_response,
            timestamp=time.time(),
            message_type="response"
        )
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph."""
        if not self._is_initialized:
            await self.initialize()
            
        await super().update_knowledge_graph(update_data)
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph."""
        if not self._is_initialized:
            await self.initialize()
            
        return await super().query_knowledge_graph(query)
        
    def get_message_history(self) -> List[AgentMessage]:
        """Get message history."""
        return self._message_history
        
    def get_knowledge_graph_updates(self) -> List[Dict[str, Any]]:
        """Get knowledge graph updates."""
        return self._knowledge_graph_updates
        
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        if not self._is_initialized:
            await self.initialize()
            
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": await self.get_capabilities(),
            "config": self.config,
            "message_count": len(self._message_history),
            "update_count": len(self._knowledge_graph_updates)
        }
        
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        self._message_history.clear()
        self._knowledge_graph_updates.clear()
        await super().cleanup()

class ResearchTestAgent(BaseTestAgent):
    """Test agent for research operations."""
    
    def __init__(self, agent_id: str = None, agent_type: str = "research", capabilities: Set[Capability] = None, **kwargs):
        # Preserve optional workflow dependencies so workflow manager can trigger
        # downstream agents in dependency tests.
        self.dependencies = list(kwargs.pop("dependencies", []))

        if capabilities is None:
            # Include both generic and test-specific research capabilities so
            # WorkflowManager can match required "research" capability while
            # tests that inspect test-specific enums still succeed.
            capabilities = {
                Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
                Capability(CapabilityType.RESEARCH, "1.0"),  # generic enum used by WorkflowManager tests
                Capability(CapabilityType.TEST_RESEARCH_AGENT, "1.0"),
            }
        from kg.models.graph_manager import KnowledgeGraphManager
        kg = KnowledgeGraphManager()
        super().__init__(
            agent_id=agent_id or "test_research_agent",
            agent_type=agent_type,
            capabilities=capabilities,
            default_response={"status": "research_completed", "findings": "Test findings"},
            knowledge_graph=kg
        )
        self._initialized = False
        self._knowledge_graph_updates = []
        self.knowledge_graph = kg
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        if not self._initialized:
            await super().initialize()
            self._initialized = True
            
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process a message."""
        if not self._initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        # Add message to history
        self._message_history.append(message)
        
        # Return default response
        import time as _t
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=self._default_response or {"status": "processed"},
            message_type="response",
            timestamp=_t.time()
        )
        
    async def update_knowledge_graph(self, data: Dict[str, Any]) -> None:
        """Update the knowledge graph with new data."""
        if not self._initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        # Preserve original dict exactly for tests that compare equality.
        self._knowledge_graph_updates.append(data)
        
    def get_message_history(self) -> List[AgentMessage]:
        """Get message history."""
        return self._message_history
        
    def get_knowledge_graph_updates(self) -> List[Dict[str, Any]]:
        """Get knowledge graph updates."""
        return self._knowledge_graph_updates
        
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        if not self._initialized:
            await self.initialize()
            
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": await self.get_capabilities(),
            "config": self.config,
            "message_count": len(self._message_history),
            "update_count": len(self._knowledge_graph_updates)
        }
        
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        self._message_history.clear()
        self._knowledge_graph_updates.clear()
        await super().cleanup()

    # WorkflowManager calls execute(payload) when available. Implement a simple handler that
    # records the call and returns a success marker so workflow tests can confirm execution.
    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()

        self._message_history.append({
            "timestamp": time.time(),
            "payload": payload,
            "type": "execute"
        })
        return {"status": "ok"}

    # Tests access .capabilities directly expecting a list of strings but also
    # use `await agent.capabilities` in other modules. Provide awaitable list.
    @property
    def capabilities(self):  # type: ignore[override]
        # For research agent keep original string list for direct access but
        # make it awaitable to underlying capability objects as well.
        return BaseTestAgent._AwaitableCaps(["research", "reasoning"], self.get_capabilities)

    async def query_knowledge_graph(self, query: Dict[str, Any]):
        """Override to record raw query dict only."""
        self._knowledge_graph_queries.append(query)
        return {"result": "test_result"}

    def get_knowledge_graph_queries(self):
        return self._knowledge_graph_queries

class DataProcessorTestAgent(BaseTestAgent):
    """Test agent for data processing tasks."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "data_processor",
        capabilities: Optional[Set[Capability]] = None,
        config: Optional[Dict[str, Any]] = None,
        default_response: Optional[Dict[str, Any]] = None,
        knowledge_graph: Optional[KnowledgeGraphManager] = None,
        **kwargs
    ):
        # Preserve workflow-specific dependencies list to enable dependency execution tests.
        self.dependencies = list(kwargs.pop("dependencies", []))

        default_capabilities = {
            Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
            Capability(CapabilityType.DATA_PROCESSING, "1.0"),
            Capability(CapabilityType.DATA_ANALYSIS, "1.0"),
            Capability(CapabilityType.TEST_DATA_PROCESSOR, "1.0"),
            Capability(CapabilityType.MONITORING, "1.0"),
            Capability(CapabilityType.SUPERVISION, "1.0")
        }
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=set(capabilities) if capabilities else default_capabilities,
            config=config,
            default_response=default_response,
            knowledge_graph=knowledge_graph
        )
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        if not self._is_initialized:
            await super().initialize()
            self._is_initialized = True
            
    async def get_capabilities(self) -> Set[Capability]:
        """Get agent capabilities."""
        if not self._is_initialized:
            await self.initialize()
        return self._capabilities
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message."""
        if not self._is_initialized:
            await self.initialize()
            
        self._message_history.append(message)
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=self._default_response,
            timestamp=time.time(),
            message_type="response"
        )
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph."""
        if not self._is_initialized:
            await self.initialize()
            
        await super().update_knowledge_graph(update_data)
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph."""
        if not self._is_initialized:
            await self.initialize()
            
        return await super().query_knowledge_graph(query)
        
    def get_message_history(self) -> List[AgentMessage]:
        """Get message history."""
        return self._message_history
        
    def get_knowledge_graph_updates(self) -> List[Dict[str, Any]]:
        """Get knowledge graph updates."""
        return self._knowledge_graph_updates
        
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        if not self._is_initialized:
            await self.initialize()
            
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": await self.get_capabilities(),
            "config": self.config,
            "message_count": len(self._message_history),
            "update_count": len(self._knowledge_graph_updates)
        }
        
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        self._message_history.clear()
        self._knowledge_graph_updates.clear()
        await super().cleanup()

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._is_initialized:
            await self.initialize()

        self._message_history.append({
            "timestamp": time.time(),
            "payload": payload,
            "type": "execute"
        })
        return {"status": "ok"}

class SensorTestAgent(BaseTestAgent):
    """Test agent for sensor tasks."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "sensor",
        capabilities: Optional[Set[Capability]] = None,
        config: Optional[Dict[str, Any]] = None,
        default_response: Optional[Dict[str, Any]] = None,
        knowledge_graph: Optional[KnowledgeGraphManager] = None
    ):
        default_capabilities = {
            Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
            Capability(CapabilityType.SENSOR_DATA, "1.0"),
            Capability(CapabilityType.TEST_SENSOR, "1.0"),
            Capability(CapabilityType.MONITORING, "1.0"),
            Capability(CapabilityType.SUPERVISION, "1.0")
        }
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=set(capabilities) if capabilities else default_capabilities,
            config=config,
            default_response=default_response,
            knowledge_graph=knowledge_graph
        )
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        if not self._is_initialized:
            await super().initialize()
            self._is_initialized = True
            
    async def get_capabilities(self) -> Set[Capability]:
        """Get agent capabilities."""
        if not self._is_initialized:
            await self.initialize()
        return self._capabilities
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message."""
        if not self._is_initialized:
            await self.initialize()
            
        self._message_history.append(message)
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content=self._default_response,
            timestamp=time.time(),
            message_type="response"
        )
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph."""
        if not self._is_initialized:
            await self.initialize()
            
        await super().update_knowledge_graph(update_data)
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph."""
        if not self._is_initialized:
            await self.initialize()
            
        return await super().query_knowledge_graph(query)
        
    def get_message_history(self) -> List[AgentMessage]:
        """Get message history."""
        return self._message_history
        
    def get_knowledge_graph_updates(self) -> List[Dict[str, Any]]:
        """Get knowledge graph updates."""
        return self._knowledge_graph_updates
        
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        if not self._is_initialized:
            await self.initialize()
            
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": await self.get_capabilities(),
            "config": self.config,
            "message_count": len(self._message_history),
            "update_count": len(self._knowledge_graph_updates)
        }
        
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        self._message_history.clear()
        self._knowledge_graph_updates.clear()
        await super().cleanup()

class TestableBaseAgent(BaseAgent):
    """Base class for test agents with common functionality."""

    def __init__(self, agent_id: str, capabilities: Optional[Set[Capability]] = None):
        super().__init__(agent_id)
        self._capabilities = capabilities or set()
        self._message_history = []
        self._status = {}

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message.

        Args:
            message: The message to process.

        Returns:
            AgentMessage: The response message.
        """
        # Record message in history
        self._message_history.append({
            'timestamp': time.time(),
            'content': message.content,
            'type': message.type
        })

        # Return default response
        return AgentMessage(
            content=f"Processed message: {message.content}",
            type=message.type,
            sender_id=self.agent_id
        )

    async def get_capabilities(self) -> Set[Capability]:
        """Get the agent's capabilities."""
        return self._capabilities

    async def get_status(self) -> Dict[str, Any]:
        """Get the agent's current status."""
        return {
            'agent_id': self.agent_id,
            'capabilities': [str(c) for c in self._capabilities],
            'message_count': len(self._message_history),
            'last_message': self._message_history[-1] if self._message_history else None
        }

class SensorAgent(TestableBaseAgent):
    """Test agent for sensor data processing."""

    def __init__(self, agent_id: str, capabilities: Optional[Set[Capability]] = None):
        super().__init__(agent_id, capabilities)
        self._sensor_data = []

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process sensor data messages.

        Args:
            message: The message to process.

        Returns:
            AgentMessage: The response message.
        """
        # Record sensor data
        self._sensor_data.append({
            'timestamp': time.time(),
            'data': message.content
        })

        # Return response
        return AgentMessage(
            content=f"Processed sensor data: {message.content}",
            type=message.type,
            sender_id=self.agent_id
        )

class DataProcessorAgent(TestableBaseAgent):
    """Test agent for data processing."""

    def __init__(self, agent_id: str, capabilities: Optional[Set[Capability]] = None):
        super().__init__(agent_id, capabilities)
        self._processed_data = []

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process data messages.

        Args:
            message: The message to process.

        Returns:
            AgentMessage: The response message.
        """
        # Record processed data
        self._processed_data.append({
            'timestamp': time.time(),
            'data': message.content
        })

        # Return response
        return AgentMessage(
            content=f"Processed data: {message.content}",
            type=message.type,
            sender_id=self.agent_id
        )

class AgenticPromptAgent(TestableBaseAgent):
    """Test agent for prompt generation and code review."""

    def __init__(self, agent_id: str, capabilities: Optional[Set[Capability]] = None):
        super().__init__(agent_id, capabilities)
        self._prompts = []
        self._code_reviews = []

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process messages for prompt generation or code review.

        Args:
            message: The message to process.

        Returns:
            AgentMessage: The response message.
        """
        if message.type == MessageType.CODE_REVIEW:
            # Handle code review
            self._code_reviews.append({
                'timestamp': time.time(),
                'code': message.content
            })
            return AgentMessage(
                content=f"Completed code review for: {message.content}",
                type=message.type,
                sender_id=self.agent_id
            )
        else:
            # Handle prompt generation
            self._prompts.append({
                'timestamp': time.time(),
                'prompt': message.content
            })
            return AgentMessage(
                content=f"Generated prompt: {message.content}",
                type=message.type,
                sender_id=self.agent_id
            ) 