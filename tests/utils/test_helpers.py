import pytest
import pytest_asyncio
import asyncio
import logging
from typing import Dict, Any, Optional, Set, List
from loguru import logger
import sys
from agents.core.base_agent import BaseAgent, AgentStatus
from agents.core.message_types import AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from kg.models.graph_manager import KnowledgeGraphManager
from agents.core.agent_registry import AgentRegistry
from datetime import datetime

class TestResourceManager:
    """Manages test resources and cleanup."""
    
    def __init__(self):
        self._resources = []
        self._tasks = set()
        
    def add_resource(self, resource):
        """Add a resource to be cleaned up."""
        self._resources.append(resource)
        
    def add_task(self, task):
        """Add a task to be cancelled."""
        self._tasks.add(task)
        
    async def cleanup(self):
        """Clean up all resources and cancel tasks."""
        # Cancel tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
        # Clean up resources
        for resource in reversed(self._resources):
            if hasattr(resource, 'cleanup'):
                await resource.cleanup()
            elif hasattr(resource, 'close'):
                await resource.close()
        self._resources.clear()

@pytest.fixture(autouse=True)
def setup_logging():
    """Setup and teardown logging for tests."""
    # Remove default handler
    logger.remove()
    
    # Add test-specific handler
    logger.add(
        sys.stderr,
        format="{time} | {level} | {message}",
        level="DEBUG",
        backtrace=True,
        diagnose=True
    )
    
    yield
    
    # Cleanup logging
    logger.remove()
    
    # Clean up root logger handlers
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        handler.close()
        root_logger.removeHandler(handler)

@pytest_asyncio.fixture
async def resource_manager():
    """Create a resource manager for test cleanup."""
    manager = TestResourceManager()
    yield manager
    await manager.cleanup()

@pytest_asyncio.fixture
async def knowledge_graph():
    """Create a knowledge graph instance for testing."""
    kg = KnowledgeGraphManager()
    try:
        await kg.initialize()
        # Verify initialization
        assert await kg.is_initialized(), "Knowledge graph failed to initialize"
        # Initialize namespaces
        kg.initialize_namespaces()
        yield kg
    finally:
        if kg:
            try:
                await kg.cleanup()
                await kg.shutdown()
            except Exception as e:
                logger.error(f"Failed to cleanup knowledge graph: {str(e)}")
                raise

@pytest_asyncio.fixture
async def agent_registry():
    """Create an agent registry instance for testing."""
    registry = AgentRegistry()
    try:
        await registry.initialize()
        # Verify initialization
        assert registry.is_initialized, "Agent registry failed to initialize"
        yield registry
    finally:
        if registry:
            try:
                await registry.cleanup()
                await registry.shutdown()
            except Exception as e:
                logger.error(f"Failed to cleanup agent registry: {str(e)}")
                raise

class EnhancedMockAgent(BaseAgent):
    """Enhanced mock agent for testing with additional functionality."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "test",
        capabilities: Optional[Set[Capability]] = None,
        default_response: Optional[Dict] = None,
        dependencies: Optional[List[str]] = None
    ):
        super().__init__(agent_id, agent_type, capabilities)
        self.default_response = default_response or {"status": "processed"}
        self.dependencies = dependencies or []
        self._message_history: List[AgentMessage] = []
        self._knowledge_graph_updates: List[Dict[str, Any]] = []
        self._knowledge_graph_queries: List[Dict[str, Any]] = []
        
    async def initialize(self) -> None:
        """Initialize the agent with proper error handling."""
        try:
            if not self.knowledge_graph:
                self.knowledge_graph = KnowledgeGraphManager()
                self.knowledge_graph.initialize_namespaces()
            await super().initialize()
            try:
                await self._initialize_kg_state()
            except Exception as e:
                self.logger.error(f"Failed to initialize knowledge graph state: {str(e)}")
                self._is_initialized = False
                self.status = AgentStatus.ERROR
                raise
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.agent_id}: {str(e)}")
            self._is_initialized = False
            self.status = AgentStatus.ERROR
            raise
            
    async def _initialize_kg_state(self) -> None:
        """Initialize knowledge graph state with proper error handling."""
        try:
            if not self.knowledge_graph:
                raise RuntimeError("Knowledge graph not initialized")
                
            # Clear existing state - use specific predicates instead of None
            await self.knowledge_graph.remove_triple(
                self.agent_uri(),
                "http://example.org/agent/hasType",
                None
            )
            await self.knowledge_graph.remove_triple(
                self.agent_uri(),
                "http://example.org/agent/hasStatus",
                None
            )
            await self.knowledge_graph.remove_triple(
                self.agent_uri(),
                "http://example.org/agent/hasRecoveryAttempts",
                None
            )
            await self.knowledge_graph.remove_triple(
                self.agent_uri(),
                "http://example.org/agent/hasLastRecoveryTime",
                None
            )
            await self.knowledge_graph.remove_triple(
                self.agent_uri(),
                "http://example.org/agent/hasMetric",
                None
            )
            await self.knowledge_graph.remove_triple(
                self.agent_uri(),
                "http://example.org/agent/hasCapability",
                None
            )
            
            # Add initial state
            await self.knowledge_graph.add_triple(
                self.agent_uri(),
                "http://example.org/agent/hasType",
                self.agent_type
            )
            await self.knowledge_graph.add_triple(
                self.agent_uri(),
                "http://example.org/agent/hasStatus",
                "http://example.org/agent/idle"
            )
            await self.knowledge_graph.add_triple(
                self.agent_uri(),
                "http://example.org/agent/hasRecoveryAttempts",
                "0"
            )
            await self.knowledge_graph.add_triple(
                self.agent_uri(),
                "http://example.org/agent/hasLastRecoveryTime",
                datetime.now().isoformat()
            )
            await self.knowledge_graph.add_triple(
                self.agent_uri(),
                "http://example.org/agent/hasMetric",
                "recovery_success"
            )
            
            # Add capabilities
            for capability in await self.get_capabilities():
                await self.knowledge_graph.add_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasCapability",
                    str(capability)
                )
        except Exception as e:
            self.logger.error(f"Failed to initialize knowledge graph state: {str(e)}")
            raise
            
    async def cleanup(self) -> None:
        """Clean up agent resources with proper error handling."""
        try:
            if self.knowledge_graph:
                # Remove all triples for this agent
                await self.knowledge_graph.remove_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasType",
                    None
                )
                await self.knowledge_graph.remove_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasStatus",
                    None
                )
                await self.knowledge_graph.remove_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasRecoveryAttempts",
                    None
                )
                await self.knowledge_graph.remove_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasLastRecoveryTime",
                    None
                )
                await self.knowledge_graph.remove_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasMetric",
                    None
                )
                await self.knowledge_graph.remove_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasCapability",
                    None
                )
            self._is_initialized = False
            self.logger.info("Cleaned up agent resources")
        except Exception as e:
            self.logger.error(f"Failed to cleanup agent resources: {str(e)}")
            raise
            
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process a message with proper error handling."""
        try:
            async with asyncio.timeout(1.0):
                async with self._lock:
                    self._message_history.append(message)
                    return AgentMessage(
                        sender_id=self.agent_id,
                        recipient_id=message.sender_id,
                        content=self.default_response,
                        timestamp=message.timestamp,
                        message_type="response"
                    )
        except asyncio.TimeoutError:
            self.logger.error("Message processing timed out")
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "error", "error": "timeout"},
                timestamp=message.timestamp,
                message_type="error"
            )
        except Exception as e:
            self.logger.error(f"Failed to process message: {str(e)}")
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "error", "error": str(e)},
                timestamp=message.timestamp,
                message_type="error"
            )
            
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update knowledge graph with proper error handling."""
        try:
            self._knowledge_graph_updates.append(update_data)
            if self.knowledge_graph:
                for key, value in update_data.items():
                    await self.knowledge_graph.add_triple(
                        self.agent_uri(),
                        f"http://example.org/agent/{key}",
                        str(value)
                    )
        except Exception as e:
            self.logger.error(f"Failed to update knowledge graph: {str(e)}")
            raise
            
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query knowledge graph with proper error handling."""
        try:
            self._knowledge_graph_queries.append(query)
            if self.knowledge_graph:
                return await self.knowledge_graph.query(query)
            return {}
        except Exception as e:
            self.logger.error(f"Failed to query knowledge graph: {str(e)}")
            raise
        
    def agent_uri(self) -> str:
        """Get the agent's URI."""
        return f"http://example.org/agent/{self.agent_id}"
        
    def get_message_history(self) -> List[AgentMessage]:
        """Get message history."""
        return self._message_history.copy()
        
    def get_knowledge_graph_updates(self) -> List[Dict[str, Any]]:
        """Get knowledge graph updates."""
        return self._knowledge_graph_updates.copy()
        
    def get_knowledge_graph_queries(self) -> List[Dict[str, Any]]:
        """Get knowledge graph queries."""
        return self._knowledge_graph_queries.copy() 