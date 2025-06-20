import pytest
import asyncio
from typing import Dict, Any, AsyncGenerator
import pytest_asyncio
from dotenv import load_dotenv
from agents.core.agent_factory import AgentFactory
from agents.core.agent_registry import AgentRegistry
from agents.core.workflow_manager import WorkflowManager
from agents.core.workflow_persistence import WorkflowPersistence
from agents.core.capability_types import CapabilityType, Capability
from kg.models.graph_manager import KnowledgeGraphManager
from tests.utils.test_agents import TestAgent, TestCapabilityAgent
import sys

# Load environment variables from .env file
load_dotenv()

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the entire test session."""
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    # Clean up all pending tasks
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    # Run loop to complete cancellation of tasks
    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    loop.close()

@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Provide test configuration settings."""
    return {
        "test_client": {
            "name": "Test Healthcare Provider",
            "type": "Healthcare",
            "size": "Large"
        },
        "test_engagement": {
            "budget_range": ["$5M", "$10M", "$20M", "$50M"],
            "timeline_range": ["6 months", "12 months", "18 months", "24 months"],
            "scope_types": [
                "Digital Transformation",
                "AI Implementation",
                "Process Optimization",
                "Strategic Planning"
            ]
        },
        "knowledge_graph": {
            "namespaces": [
                "http://example.org/demo/",
                "http://example.org/demo/consulting/",
                "http://example.org/demo/task/",
                "http://example.org/demo/agent/",
                "http://example.org/agent/",
                "http://example.org/event/",
                "http://example.org/domain/",
                "http://example.org/system/",
                "http://example.org/core#",
                "http://example.org/swarm#",
                "http://example.org/swarm-ex#"
            ]
        }
    }

@pytest.fixture(scope="session")
async def registry() -> AsyncGenerator:
    """Create a registry instance for the entire test session."""
    from agents.core.agent_registry import AgentRegistry
    registry = AgentRegistry()
    await registry.initialize()
    yield registry
    await registry.cleanup()

@pytest.fixture(scope="function")
async def workflow_manager(registry) -> AsyncGenerator:
    """Create a workflow manager instance for each test."""
    from agents.core.workflow_manager import WorkflowManager
    manager = WorkflowManager(registry)
    await manager.initialize()
    yield manager
    await manager.shutdown()

@pytest.fixture(scope="function")
async def knowledge_graph() -> AsyncGenerator:
    """Create a knowledge graph instance for each test."""
    from kg.models.graph_manager import KnowledgeGraphManager
    kg = KnowledgeGraphManager()
    await kg.initialize()
    yield kg
    await kg.shutdown()

@pytest.fixture(scope="function")
async def test_agent(registry) -> AsyncGenerator:
    """Create a test agent instance for each test."""
    from tests.utils.test_agents import TestAgent
    agent = TestAgent(agent_id="test_agent")
    await agent.initialize()
    yield agent
    await agent.cleanup()

@pytest.fixture
async def agent_factory(knowledge_graph):
    """Create agent factory with test agent templates."""
    factory = AgentFactory(registry=None, knowledge_graph=knowledge_graph)
    await factory.initialize()
    
    # Register test agent templates with capabilities
    await factory.register_agent_template("test_agent", TestAgent)
    await factory.register_agent_template("capability_agent", TestCapabilityAgent)
    await factory.register_agent_template("supervisor", TestCapabilityAgent)
    await factory.register_agent_template("worker_0", TestCapabilityAgent)
    await factory.register_agent_template("monitor", TestCapabilityAgent)
    
    return factory

@pytest.fixture
async def agent_registry(agent_factory, knowledge_graph):
    """Create agent registry with test agents."""
    registry = AgentRegistry()
    
    # Create and register test agents with capabilities
    test_agent = await agent_factory.create_agent("test_agent", "test_agent_1")
    await test_agent.initialize()
    test_capabilities = await test_agent.get_capabilities()
    await registry.register_agent(test_agent, test_capabilities)
    
    capability_agent = await agent_factory.create_agent("capability_agent", "capability_agent_1")
    await capability_agent.initialize()
    capability_agent_capabilities = await capability_agent.get_capabilities()
    await registry.register_agent(capability_agent, capability_agent_capabilities)
    
    supervisor = await agent_factory.create_agent("supervisor", "supervisor_1")
    await supervisor.initialize()
    supervisor_capabilities = await supervisor.get_capabilities()
    await registry.register_agent(supervisor, supervisor_capabilities)
    
    worker = await agent_factory.create_agent("worker_0", "worker_1")
    await worker.initialize()
    worker_capabilities = await worker.get_capabilities()
    await registry.register_agent(worker, worker_capabilities)
    
    monitor = await agent_factory.create_agent("monitor", "monitor_1")
    await monitor.initialize()
    monitor_capabilities = await monitor.get_capabilities()
    await registry.register_agent(monitor, monitor_capabilities)
    
    return registry

# ---------------------------------------------------------------------------
# Compatibility fixture: some workflow_manager tests expect `test_agents`.
# Provide a small dict of pre-initialized agents keyed by role.
# ---------------------------------------------------------------------------

@pytest.fixture
async def test_agents(agent_factory):
    """Dictionary of commonly used test agents (worker / monitor / supervisor)."""
    agents = {}

    # Create worker
    worker = await agent_factory.create_agent("worker_0", "worker_1")
    await worker.initialize()
    agents["worker"] = worker

    # Create monitor
    monitor = await agent_factory.create_agent("monitor", "monitor_1")
    await monitor.initialize()
    agents["monitor"] = monitor

    # Create supervisor
    supervisor = await agent_factory.create_agent("supervisor", "supervisor_1")
    await supervisor.initialize()
    agents["supervisor"] = supervisor

    yield agents

    # Cleanup
    for a in agents.values():
        await a.cleanup() 