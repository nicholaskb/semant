import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from agents.core.base_agent import BaseAgent, AgentStatus, AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from agents.core.agent_registry import AgentRegistry
from agents.core.agent_factory import AgentFactory
from agents.core.workflow_notifier import WorkflowNotifier
from kg.models.graph_manager import KnowledgeGraphManager
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
import time
from typing import Dict, Any
import threading

class TestRecoveryAgent(BaseAgent):
    """Test agent for recovery testing."""
    AGENT_NS = "http://example.org/agent/"
    STATUS_NS = "http://example.org/agent/"
    TYPE_NS = "http://example.org/agent/"
    RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    AGENT_CLASS = "http://example.org/agent/Agent"
    HAS_STATUS = "http://example.org/agent/hasStatus"
    HAS_RECOVERY_ATTEMPTS = "http://example.org/agent/hasRecoveryAttempts"
    HAS_TYPE = "http://example.org/agent/hasType"
    HAS_ROLE = "http://example.org/agent/hasRole"
    HAS_METRIC = "http://example.org/agent/hasMetric"
    HAS_METRIC_VALUE = "http://example.org/agent/hasMetricValue"
    HAS_RECOVERY_TIME = "http://example.org/agent/lastRecoveryTime"
    STATUS_IDLE = "http://example.org/agent/idle"
    STATUS_ERROR = "http://example.org/agent/error"
    
    def __init__(self, agent_id: str, agent_type: str = "recovery_test", capabilities=None, config=None):
        if capabilities is None or not capabilities:
            capabilities = {Capability(CapabilityType.TASK_EXECUTION, version="1.0")}
        super().__init__(
            agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            config=config
        )
        self.recovery_attempts = 0
        self.max_recovery_attempts = config.get("max_recovery_attempts", 3) if config else 3
        self.recovery_timeout = config.get("recovery_timeout", 1.0) if config else 1.0
        self._kg_updates = []
        self._kg_queries = []
        self.status = AgentStatus.IDLE
        self._lock = asyncio.Lock()
        self._should_fail = False  # Flag to control recovery success/failure
        self._tasks = set()  # Track pending tasks
        
    def agent_uri(self):
        return f"{self.AGENT_NS}{self.agent_id}"
        
    async def initialize(self):
        """Initialize the agent."""
        try:
            async with asyncio.timeout(2.0):  # Add timeout
                await super().initialize()
                if self.knowledge_graph:
                    async with self._lock:
                        # Clear any existing triples
                        await self.knowledge_graph.remove_triple(self.agent_uri(), None, None)
                        # Add initial triples
                        await self.knowledge_graph.add_triple(
                            self.agent_uri(),
                            self.RDF_TYPE,
                            self.AGENT_CLASS
                        )
                        await self.knowledge_graph.add_triple(
                            self.agent_uri(),
                            self.HAS_STATUS,
                            self.STATUS_IDLE
                        )
                        await self.knowledge_graph.add_triple(
                            self.agent_uri(),
                            self.HAS_RECOVERY_ATTEMPTS,
                            "0"
                        )
                        await self.knowledge_graph.add_triple(
                            self.agent_uri(),
                            self.HAS_TYPE,
                            self.agent_type
                        )
                        if hasattr(self, 'role'):
                            await self.knowledge_graph.add_triple(
                                self.agent_uri(),
                                self.HAS_ROLE,
                                self.role
                            )
        except asyncio.TimeoutError:
            self.logger.error("Initialization timed out")
            raise
        
    async def _update_status_in_kg(self, status_uri: str):
        """Update agent status in knowledge graph with lock protection."""
        if self.knowledge_graph:
            try:
                async with asyncio.timeout(1.0):  # Add timeout
                    async with self._lock:
                        # Remove old status triple(s)
                        await self.knowledge_graph.remove_triple(self.agent_uri(), self.HAS_STATUS, None)
                        # Add new status triple
                        await self.knowledge_graph.add_triple(self.agent_uri(), self.HAS_STATUS, status_uri)
            except asyncio.TimeoutError:
                self.logger.error("Status update timed out")
                raise

    async def _update_recovery_attempts_in_kg(self):
        """Update recovery attempts in knowledge graph with lock protection."""
        if self.knowledge_graph:
            try:
                async with asyncio.timeout(1.0):  # Add timeout
                    async with self._lock:
                        await self.knowledge_graph.remove_triple(self.agent_uri(), self.HAS_RECOVERY_ATTEMPTS, None)
                        await self.knowledge_graph.add_triple(self.agent_uri(), self.HAS_RECOVERY_ATTEMPTS, str(self.recovery_attempts))
            except asyncio.TimeoutError:
                self.logger.error("Recovery attempts update timed out")
                raise

    async def _update_recovery_metrics(self, recovery_time: float):
        """Update recovery metrics in knowledge graph."""
        if self.knowledge_graph:
            try:
                async with asyncio.timeout(1.0):  # Add timeout
                    async with self._lock:
                        metric_uri = f"{self.agent_uri()}/metrics/recovery"
                        await self.knowledge_graph.add_triple(
                            self.agent_uri(),
                            self.HAS_METRIC,
                            metric_uri
                        )
                        await self.knowledge_graph.add_triple(
                            metric_uri,
                            self.HAS_METRIC_VALUE,
                            str(self.recovery_attempts)
                        )
                        await self.knowledge_graph.add_triple(
                            metric_uri,
                            self.HAS_RECOVERY_TIME,
                            str(recovery_time)
                        )
            except asyncio.TimeoutError:
                self.logger.error("Metrics update timed out")
                raise

    async def recover(self):
        """Test recovery implementation with improved status and KG handling."""
        start_time = time.time()
        try:
            async with asyncio.timeout(self.recovery_timeout):  # Use configured timeout
                async with self._lock:
                    # Check max attempts before incrementing
                    if self.recovery_attempts >= self.max_recovery_attempts:
                        self.status = AgentStatus.ERROR
                        await self._update_status_in_kg(self.STATUS_ERROR)
                        return False

                    self.recovery_attempts += 1
                    self.logger.debug(f"Recovery attempt {self.recovery_attempts}")
                    await self._update_recovery_attempts_in_kg()

                    # Simulate recovery delay
                    await asyncio.sleep(0.1)

                    # If recovery fails (controlled by _should_fail flag), set ERROR and update KG
                    if self._should_fail:
                        self.status = AgentStatus.ERROR
                        await self._update_status_in_kg(self.STATUS_ERROR)
                        await self._update_recovery_metrics(time.time() - start_time)
                        return False

                    # If recovery succeeds, set IDLE and update KG
                    self.status = AgentStatus.IDLE
                    await self._update_status_in_kg(self.STATUS_IDLE)
                    await self._update_recovery_metrics(time.time() - start_time)
                    return True
        except asyncio.TimeoutError:
            self.logger.error("Recovery operation timed out")
            self.status = AgentStatus.ERROR
            await self._update_status_in_kg(self.STATUS_ERROR)
            await self._update_recovery_metrics(time.time() - start_time)
            return False
        except Exception as e:
            self.logger.error(f"Recovery failed: {e}")
            self.status = AgentStatus.ERROR
            await self._update_status_in_kg(self.STATUS_ERROR)
            await self._update_recovery_metrics(time.time() - start_time)
            return False

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process a message and handle errors."""
        try:
            async with asyncio.timeout(1.0):  # Add timeout
                async with self._lock:
                    if message.content.get("trigger_error", False):
                        self.status = AgentStatus.ERROR
                        if self.knowledge_graph:
                            await self._update_status_in_kg(self.STATUS_ERROR)
                        return {"status": "error"}
                    return {"status": "success"}
        except asyncio.TimeoutError:
            self.logger.error("Message processing timed out")
            return {"status": "error", "error": "timeout"}
        except Exception as e:
            self.logger.error(f"Message processing failed: {e}")
            async with self._lock:
                self.status = AgentStatus.ERROR
                if self.knowledge_graph:
                    await self._update_status_in_kg(self.STATUS_ERROR)
                return {"status": "error", "error": str(e)}

    async def update_knowledge_graph(self, update_data: dict) -> None:
        """Update the knowledge graph with new information."""
        self._kg_updates.append(update_data)
        if self.knowledge_graph:
            for subject, properties in update_data.items():
                for predicate, value in properties.items():
                    await self.knowledge_graph.add_triple(subject, predicate, value)

    async def query_knowledge_graph(self, query: dict) -> dict:
        """Query the knowledge graph."""
        self._kg_queries.append(query)
        if self.knowledge_graph:
            return await self.knowledge_graph.query_graph(query.get("sparql", ""))
        return {}

    def get_knowledge_graph_updates(self):
        """Get all knowledge graph updates."""
        return self._kg_updates

    def get_knowledge_graph_queries(self):
        """Get all knowledge graph queries."""
        return self._kg_queries

    async def cleanup(self):
        """Clean up resources and cancel pending tasks."""
        self.logger.debug("Starting cleanup")
        # Cancel all pending tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self.logger.debug("Cleanup completed")

    def set_should_fail(self, should_fail: bool):
        """Set whether recovery should fail."""
        self._should_fail = should_fail

@pytest_asyncio.fixture(scope="function")
async def setup_recovery_test(event_loop):
    """Set up test environment for recovery testing."""
    registry = AgentRegistry()
    knowledge_graph = KnowledgeGraphManager()
    await knowledge_graph.initialize()
    factory = AgentFactory(registry, knowledge_graph)
    
    # Register recovery_test agent template
    await factory.register_agent_template(
        "recovery_test",
        TestRecoveryAgent,
        {CapabilityType.TASK_EXECUTION}
    )
    
    # Create and register test agent
    agent = TestRecoveryAgent("test_agent")
    agent.knowledge_graph = knowledge_graph
    await agent.initialize()
    await registry.register_agent(agent, await agent.capabilities)
    
    try:
        yield registry, knowledge_graph, factory
    finally:
        # Cleanup
        if hasattr(knowledge_graph, 'shutdown'):
            await knowledge_graph.shutdown()
        await registry.cleanup()
        # Cancel any pending tasks
        for task in asyncio.all_tasks(event_loop):
            if not task.done():
                task.cancel()
        # Wait for tasks to complete
        await asyncio.gather(*asyncio.all_tasks(event_loop), return_exceptions=True)

@pytest_asyncio.fixture(scope="function")
async def agent_registry(event_loop):
    """Create a fresh agent registry for each test."""
    registry = AgentRegistry()
    notifier = WorkflowNotifier()
    await notifier.initialize()
    registry.notifier = notifier
    
    try:
        yield registry
    finally:
        await registry.cleanup()
        # Cancel any pending tasks
        for task in asyncio.all_tasks(event_loop):
            if not task.done():
                task.cancel()
        # Wait for tasks to complete
        await asyncio.gather(*asyncio.all_tasks(event_loop), return_exceptions=True)

@pytest.mark.asyncio
async def test_agent_recovery(agent_registry):
    """Test basic agent recovery functionality."""
    agent = TestRecoveryAgent("test_agent")
    agent.set_should_fail(False)  # Ensure recovery succeeds
    await agent_registry.register_agent(agent)
    
    try:
        async with asyncio.timeout(2.0):  # Add timeout
            # Test successful recovery
            success = await agent_registry.recover_agent("test_agent")
            assert success
            assert agent.status == AgentStatus.IDLE
            assert agent.recovery_attempts == 1
            
            # Verify knowledge graph state
            kg_state = await agent.query_knowledge_graph({
                "sparql": """
                    SELECT ?status ?recovery_attempts WHERE {
                        <http://example.org/agent/test_agent> <http://example.org/agent/hasStatus> ?status ;
                                         <http://example.org/agent/hasRecoveryAttempts> ?recovery_attempts .
                    }
                """
            })
            assert kg_state
            assert kg_state[0]["status"] == "http://example.org/agent/idle"
            assert int(kg_state[0]["recovery_attempts"]) == 1
    except asyncio.TimeoutError:
        pytest.fail("Test timed out")

@pytest.mark.asyncio
async def test_max_recovery_attempts(agent_registry):
    """Test that recovery stops after maximum attempts."""
    agent = TestRecoveryAgent("test_agent")
    agent.recovery_attempts = 3  # Set to max attempts
    agent.set_should_fail(True)  # Make recovery fail
    await agent_registry.register_agent(agent)
    
    try:
        async with asyncio.timeout(2.0):  # Add timeout
            # Attempt recovery
            success = await agent_registry.recover_agent("test_agent")
            assert not success
            assert agent.status == AgentStatus.ERROR
            assert agent.recovery_attempts == 3  # Should not increment
            
            # Verify knowledge graph state
            kg_state = await agent.query_knowledge_graph({
                "sparql": """
                    SELECT ?status ?recovery_attempts WHERE {
                        <http://example.org/agent/test_agent> <http://example.org/agent/hasStatus> ?status ;
                                         <http://example.org/agent/hasRecoveryAttempts> ?recovery_attempts .
                    }
                """
            })
            assert kg_state
            assert kg_state[0]["status"] == "http://example.org/agent/error"
            assert int(kg_state[0]["recovery_attempts"]) == 3
    except asyncio.TimeoutError:
        pytest.fail("Test timed out")

@pytest.mark.asyncio
async def test_agent_recovery_timeout(agent_registry):
    """Test agent recovery timeout handling."""
    agent = TestRecoveryAgent("test_agent")
    agent.recovery_timeout = 0.1  # Set short timeout
    agent.set_should_fail(False)  # Make recovery succeed but slow
    await agent_registry.register_agent(agent)
    
    # Make recovery take longer than timeout
    original_recover = agent.recover
    async def slow_recover():
        try:
            await asyncio.sleep(0.2)  # This should trigger timeout
            return True
        except asyncio.CancelledError:
            # Handle cancellation from timeout
            agent.status = AgentStatus.ERROR
            return False
    agent.recover = slow_recover
    
    # Attempt recovery
    success = await agent_registry.recover_agent("test_agent")
    assert not success
    assert agent.status == AgentStatus.ERROR
    assert agent.recovery_attempts == 1
    
    # Restore original recover method
    agent.recover = original_recover
    
    # Verify knowledge graph state
    kg_state = await agent.query_knowledge_graph({
        "sparql": """
            SELECT ?status ?recovery_attempts WHERE {
                <http://example.org/agent/test_agent> <http://example.org/agent/hasStatus> ?status ;
                                     <http://example.org/agent/hasRecoveryAttempts> ?recovery_attempts .
            }
        """
    })
    assert kg_state
    assert kg_state[0]["status"] == "http://example.org/agent/error"
    assert int(kg_state[0]["recovery_attempts"]) == 1

@pytest.mark.asyncio
async def test_role_recovery(agent_registry):
    """Test recovery of agents with specific roles."""
    agent = TestRecoveryAgent("test_agent")
    agent.role = "test_role"
    agent.set_should_fail(False)  # Ensure recovery succeeds
    await agent_registry.register_agent(agent)
    
    # Test role persistence during recovery
    success = await agent_registry.recover_agent("test_agent")
    assert success
    assert agent.role == "test_role"
    
    # Verify knowledge graph state
    kg_state = await agent.query_knowledge_graph({
        "sparql": """
            SELECT ?role WHERE {
                <http://example.org/agent/test_agent> <http://example.org/agent/hasRole> ?role .
            }
        """
    })
    assert kg_state
    assert kg_state[0]["role"] == "test_role"

@pytest.mark.asyncio
async def test_recovery_metrics(agent_registry):
    """Test recovery metrics collection."""
    agent = TestRecoveryAgent("test_agent")
    agent.set_should_fail(False)  # Ensure recovery succeeds
    await agent_registry.register_agent(agent)
    
    # Test metric creation during recovery
    success = await agent_registry.recover_agent("test_agent")
    assert success
    
    # Verify metric node in knowledge graph
    kg_state = await agent.query_knowledge_graph({
        "sparql": """
            SELECT ?metric ?value ?time WHERE {
                <http://example.org/agent/test_agent> <http://example.org/agent/hasMetric> ?metric .
                ?metric <http://example.org/agent/hasMetricValue> ?value ;
                       <http://example.org/agent/recoveryTime> ?time .
            }
        """
    })
    assert kg_state
    assert int(kg_state[0]["value"]) == 1
    assert float(kg_state[0]["time"]) > 0

@pytest.mark.asyncio
async def test_knowledge_graph_integration(agent_registry):
    """Test knowledge graph integration and SPARQL query functionality."""
    agent = TestRecoveryAgent("test_agent")
    agent.set_should_fail(False)  # Ensure recovery succeeds
    await agent_registry.register_agent(agent)
    
    # Test complete knowledge graph update cycle
    success = await agent_registry.recover_agent("test_agent")
    assert success
    
    # Verify all expected triples
    kg_state = await agent.query_knowledge_graph({
        "sparql": """
            SELECT ?status ?attempts ?time ?metric WHERE {
                <http://example.org/agent/test_agent> <http://example.org/agent/hasStatus> ?status ;
                                     <http://example.org/agent/hasRecoveryAttempts> ?attempts ;
                                     <http://example.org/agent/lastRecoveryTime> ?time ;
                                     <http://example.org/agent/hasMetric> ?metric .
            }
        """
    })
    assert kg_state
    assert kg_state[0]["status"] == "http://example.org/agent/idle"
    assert int(kg_state[0]["attempts"]) == 1
    assert kg_state[0]["time"]
    assert kg_state[0]["metric"] 