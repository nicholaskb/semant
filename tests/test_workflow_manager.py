import pytest
import pytest_asyncio
from typing import Dict, Any, Set
from agents.core.workflow_manager import WorkflowManager
from agents.core.base_agent import AgentMessage, BaseAgent
from agents.core.agent_registry import AgentRegistry
from tests.utils.test_agents import (
    BaseTestAgent,
    ResearchTestAgent,
    DataProcessorTestAgent,
    SensorTestAgent,
    TestAgent
)
import asyncio
from agents.core.capability_types import Capability, CapabilityType
from datetime import datetime
import time
from agents.core.workflow_persistence import WorkflowPersistence
from agents.core.workflow_types import Workflow
from agents.core.workflow_manager import WorkflowStatus
from agents.utils import AwaitableValue

@pytest_asyncio.fixture(scope="function")
async def registry():
    """Create a fresh AgentRegistry instance for each test."""
    registry = AgentRegistry()
    await registry.initialize()
    yield registry
    await registry.cleanup()  # Clean up after test

@pytest_asyncio.fixture(scope="function")
async def workflow_manager(registry):
    """Create a WorkflowManager instance with the registry."""
    # Reload to ensure latest edits to Workflow class are visible during test run
    import importlib, agents.core.workflow_manager as _wm_reload
    importlib.reload(_wm_reload)
    from agents.core.workflow_manager import WorkflowManager as _WM
    manager = _WM(registry)
    await manager.initialize()
    yield manager
    await manager.shutdown()  # Clean up after test

@pytest_asyncio.fixture
async def setup_agents(registry):
    """Set up test agents with their capabilities."""
    agents = {
        "research": ResearchTestAgent(agent_id="research_test_agent"),
        "data_processor": DataProcessorTestAgent(agent_id="data_processor_test_agent"),
        "sensor": SensorTestAgent(agent_id="sensor_test_agent")
    }
    
    # Register agents with their capabilities
    for agent in agents.values():
        await agent.initialize()  # Initialize before registration
        capabilities = await agent.capabilities
        await registry.register_agent(agent, capabilities)
    
    yield AwaitableValue(agents)
    
    # Cleanup
    for agent in agents.values():
        await agent.cleanup()

@pytest.fixture
def test_capabilities():
    return {
        Capability(type=CapabilityType.RESEARCH, version="1.0"),
        Capability(type=CapabilityType.DATA_PROCESSING, version="1.0"),
        Capability(type=CapabilityType.SENSOR_DATA, version="1.0"),
        Capability(type=CapabilityType.KNOWLEDGE_GRAPH, version="1.0")
    }

@pytest.mark.asyncio
async def test_agent_registration(registry, setup_agents):
    """Test agent registration and capability management."""
    agents = await setup_agents
    
    # Verify agents are registered
    for agent_id, agent in agents.items():
        assert agent_id in registry.agents
        assert registry.agents[agent_id] == agent
        
    # Verify capabilities are registered
    for agent in agents.values():
        agent_capabilities = await registry.get_agent_capabilities(agent.agent_id)
        agent_actual_capabilities = await agent.capabilities
        assert set(agent_capabilities) == agent_actual_capabilities
        
    # Test capability-based agent lookup
    research_agents = await registry.get_agents_by_capability(CapabilityType.RESEARCH)
    assert len(research_agents) == 1
    assert research_agents[0].agent_id == "research_test_agent"
    
    # Test capability update
    new_capabilities = {
        Capability(CapabilityType.RESEARCH, "1.0"),
        Capability(CapabilityType.NEW_CAPABILITY, "1.0")
    }
    await registry.update_agent_capabilities("research_test_agent", new_capabilities)
    updated_capabilities = await registry.get_agent_capabilities("research_test_agent")
    assert set(updated_capabilities) == new_capabilities
    
    # Test agent unregistration
    await registry.unregister_agent("research_test_agent")
    assert "research_test_agent" not in registry.agents
    research_agents = await registry.get_agents_by_capability(CapabilityType.RESEARCH)
    assert len(research_agents) == 0

@pytest.mark.asyncio
async def test_workflow_creation(workflow_manager):
    # Create a test workflow
    workflow = Workflow(
        workflow_id="test_workflow",
        name="Test Workflow",
        description="Test workflow for unit tests",
        required_capabilities={
            Capability(CapabilityType.TASK_EXECUTION, "1.0"),
            Capability(CapabilityType.MONITORING, "1.0")
        }
    )
    
    # Register workflow
    await workflow_manager.register_workflow(workflow)
    
    # Verify workflow registration
    registered_workflow = await workflow_manager.get_workflow("test_workflow")
    assert registered_workflow is not None
    assert registered_workflow.workflow_id == "test_workflow"
    assert len(registered_workflow.required_capabilities) == 2

@pytest.mark.asyncio
async def test_workflow_assembly(workflow_manager, registry):
    """Test workflow assembly."""
    # Create agent with required capability
    agent = TestAgent("agent1", capabilities={Capability(CapabilityType.RESEARCH, "1.0")})
    await agent.initialize()
    agent_capabilities = await agent.get_capabilities()
    await registry.register_agent(agent, agent_capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities={Capability(CapabilityType.RESEARCH, "1.0")}
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Verify workflow state
    workflow = await workflow_manager.get_workflow(workflow_id)
    assert workflow.status == WorkflowStatus.ASSEMBLED

@pytest.mark.asyncio
async def test_workflow_execution(workflow_manager, test_agents):
    # Create and register workflow
    workflow = Workflow(
        workflow_id="exec_workflow",
        name="Execution Workflow",
        description="Workflow for execution testing",
        required_capabilities={
            Capability(CapabilityType.TASK_EXECUTION, "1.0"),
            Capability(CapabilityType.MONITORING, "1.0")
        }
    )
    await workflow_manager.register_workflow(workflow)
    
    # Register agents
    await workflow_manager.register_agent(test_agents["worker"])
    await workflow_manager.register_agent(test_agents["monitor"])
    
    # Execute workflow
    execution = await workflow_manager.execute_workflow("exec_workflow")
    assert execution is not None
    assert execution.workflow_id == "exec_workflow"
    assert execution.status == "completed"
    
    # Verify agent assignments
    assignments = await workflow_manager.get_workflow_assignments("exec_workflow")
    assert len(assignments) == 2
    assert any(a.agent_id == "worker_1" for a in assignments)
    assert any(a.agent_id == "monitor_1" for a in assignments)

@pytest.mark.asyncio
async def test_workflow_supervision(workflow_manager, test_agents):
    # Create and register workflow
    workflow = Workflow(
        workflow_id="supervised_workflow",
        name="Supervised Workflow",
        description="Workflow with supervision",
        required_capabilities={
            Capability(CapabilityType.SUPERVISION, "1.0"),
            Capability(CapabilityType.TASK_EXECUTION, "1.0")
        }
    )
    await workflow_manager.register_workflow(workflow)
    
    # Register agents
    await workflow_manager.register_agent(test_agents["supervisor"])
    await workflow_manager.register_agent(test_agents["worker"])
    
    # Execute workflow
    execution = await workflow_manager.execute_workflow("supervised_workflow")
    assert execution is not None
    assert execution.workflow_id == "supervised_workflow"
    
    # Verify supervisor assignment
    assignments = await workflow_manager.get_workflow_assignments("supervised_workflow")
    assert len(assignments) == 2
    supervisor = next(a for a in assignments if a.agent_id == "supervisor_1")
    assert supervisor is not None
    capabilities = await supervisor.get_capabilities()
    assert any(c.type == CapabilityType.SUPERVISION for c in capabilities)

@pytest.mark.asyncio
async def test_workflow_validation(workflow_manager):
    """Test workflow validation."""
    workflow_id = await workflow_manager.create_workflow(
        name="Invalid Workflow",
        description="Workflow with missing capabilities",
        required_capabilities=["nonexistent_capability"]
    )
    
    validation = await workflow_manager.validate_workflow(workflow_id)
    assert not validation["valid"]
    assert "missing_capabilities" in validation

@pytest.mark.asyncio
async def test_load_balancing(workflow_manager, registry, test_capabilities):
    # Create multiple agents with same capability
    agent1 = TestAgent("agent1", capabilities={next(iter(test_capabilities))})
    agent2 = TestAgent("agent2", capabilities={next(iter(test_capabilities))})
    agent3 = TestAgent("agent3", capabilities={next(iter(test_capabilities))})
    
    # Initialize agents before registration
    await agent1.initialize()
    await agent2.initialize()
    await agent3.initialize()
    
    # Get capabilities after initialization
    agent1_capabilities = await agent1.get_capabilities()
    agent2_capabilities = await agent2.get_capabilities()
    agent3_capabilities = await agent3.get_capabilities()
    
    await registry.register_agent(agent1, agent1_capabilities)
    await registry.register_agent(agent2, agent2_capabilities)
    await registry.register_agent(agent3, agent3_capabilities)
    
    # Create workflow with multiple agents per capability
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities={next(iter(test_capabilities))},
        max_agents_per_capability=2
    )
    
    # Execute workflow multiple times
    for _ in range(3):
        await workflow_manager.execute_workflow(workflow_id)
        
        # Verify workflow status
        status = await workflow_manager.get_workflow_status(workflow_id)
        assert status["status"] == WorkflowStatus.COMPLETED

@pytest.mark.asyncio
async def test_workflow_metrics(workflow_manager, registry, test_capabilities):
    # Create agent and workflow
    agent = TestAgent("agent1", capabilities=test_capabilities)
    await agent.initialize()  # Initialize before registration
    agent_capabilities = await agent.get_capabilities()
    await registry.register_agent(agent, agent_capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities=test_capabilities,
        max_agents_per_capability=1
    )
    
    # Execute workflow
    await workflow_manager.execute_workflow(workflow_id)
    
    # Check workflow status
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["status"] == WorkflowStatus.COMPLETED
    
    # Check metrics
    metrics = await workflow_manager.get_workflow_metrics(workflow_id)
    assert metrics["workflow_count"] > 0
    assert metrics["completed_workflows"] > 0

@pytest.mark.asyncio
async def test_registry_state_consistency(workflow_manager, registry):
    """Test that registry state remains consistent across workflow operations."""
    # Register initial agents
    agent1 = ResearchTestAgent(agent_id="research_1")
    agent2 = ResearchTestAgent(agent_id="research_2")
    
    await agent1.initialize()  # Initialize before registration
    await agent2.initialize()  # Initialize before registration
    
    agent1_capabilities = await agent1.get_capabilities()
    agent2_capabilities = await agent2.get_capabilities()
    
    await registry.register_agent(agent1, agent1_capabilities)
    await registry.register_agent(agent2, agent2_capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities={Capability(CapabilityType.RESEARCH, "1.0")}
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Verify workflow state
    workflow = await workflow_manager.get_workflow(workflow_id)
    assert workflow.status == WorkflowStatus.ASSEMBLED

@pytest.mark.asyncio
async def test_concurrent_registration_and_assembly(workflow_manager, registry):
    """Test handling of concurrent agent registration and workflow assembly."""
    # Create workflow first
    workflow_id = await workflow_manager.create_workflow(
        name="Concurrent Test",
        description="Test concurrent registration and assembly",
        required_capabilities={Capability(CapabilityType.RESEARCH, "1.0")}
    )
    
    # Start assembly
    assembly_task = asyncio.create_task(workflow_manager.assemble_workflow(workflow_id))
    
    # Register agents during assembly
    agent1 = ResearchTestAgent(agent_id="research_1")
    await agent1.initialize()  # Initialize before registration
    agent1_capabilities = await agent1.get_capabilities()
    await registry.register_agent(agent1, agent1_capabilities)
    
    # Wait for assembly to complete
    await assembly_task
    
    # Verify workflow state
    workflow = await workflow_manager.get_workflow(workflow_id)
    assert workflow.status == WorkflowStatus.ASSEMBLED

@pytest.mark.asyncio
async def test_registry_recovery(workflow_manager, registry):
    """Test registry recovery after agent failures."""
    # Register agents
    agent1 = ResearchTestAgent(agent_id="research_1")
    agent2 = ResearchTestAgent(agent_id="research_2")
    
    await agent1.initialize()  # Initialize before registration
    await agent2.initialize()  # Initialize before registration
    
    agent1_capabilities = await agent1.get_capabilities()
    agent2_capabilities = await agent2.get_capabilities()
    
    await registry.register_agent(agent1, agent1_capabilities)
    await registry.register_agent(agent2, agent2_capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities={Capability(CapabilityType.RESEARCH, "1.0")}
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Verify workflow state
    workflow = await workflow_manager.get_workflow(workflow_id)
    assert workflow.status == WorkflowStatus.ASSEMBLED

@pytest.mark.asyncio
async def test_capability_conflicts(workflow_manager, registry):
    """Test handling of conflicting capabilities between agents."""
    # Create agents with overlapping capabilities
    agent1 = TestAgent(
        agent_id="agent_1",
        agent_type="multi_capability",
        capabilities={
            Capability(CapabilityType.CAP_A, "1.0"),
            Capability(CapabilityType.CAP_B, "1.0")
        }
    )
    agent2 = TestAgent(
        agent_id="agent_2",
        agent_type="multi_capability",
        capabilities={
            Capability(CapabilityType.CAP_B, "1.0"),
            Capability(CapabilityType.CAP_C, "1.0")
        }
    )
    
    # Initialize agents before registration
    await agent1.initialize()
    await agent2.initialize()
    
    agent1_capabilities = await agent1.get_capabilities()
    agent2_capabilities = await agent2.get_capabilities()
    
    await registry.register_agent(agent1, agent1_capabilities)
    await registry.register_agent(agent2, agent2_capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities={
            Capability(CapabilityType.CAP_A, "1.0"),
            Capability(CapabilityType.CAP_B, "1.0"),
            Capability(CapabilityType.CAP_C, "1.0")
        }
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Verify workflow state
    workflow = await workflow_manager.get_workflow(workflow_id)
    assert workflow.status == WorkflowStatus.ASSEMBLED

@pytest.mark.asyncio
async def test_registry_persistence(workflow_manager, registry):
    """Test registry persistence across workflow operations."""
    # Register agents
    agent1 = ResearchTestAgent(agent_id="research_1")
    agent2 = DataProcessorTestAgent(agent_id="processor_1")
    
    await agent1.initialize()  # Initialize before registration
    await agent2.initialize()  # Initialize before registration
    
    agent1_capabilities = await agent1.get_capabilities()
    agent2_capabilities = await agent2.get_capabilities()
    
    await registry.register_agent(agent1, agent1_capabilities)
    await registry.register_agent(agent2, agent2_capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities={
            Capability(CapabilityType.RESEARCH, "1.0"),
            Capability(CapabilityType.DATA_PROCESSING, "1.0")
        }
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Verify workflow state
    workflow = await workflow_manager.get_workflow(workflow_id)
    assert workflow.status == WorkflowStatus.ASSEMBLED

@pytest.mark.asyncio
async def test_anomaly_detection_workflow(workflow_manager, setup_agents):
    """Test a multi-agent workflow for anomaly detection and reporting."""
    # Register agents (setup_agents fixture already does this)
    # Assemble workflow requiring all three capabilities
    workflow_id = await workflow_manager.create_workflow(
        name="Anomaly Detection Workflow",
        description="Detects anomalies and provides recommendations",
        required_capabilities=["test_sensor", "test_data_processor", "test_research_agent"]
    )
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    assert assembly_result["status"] == "success"
    assert len(assembly_result["agents"]) == 3
    # Execute workflow with a high sensor reading
    initial_data = {"test_sensor": "Sensor1", "reading": 99.9}
    execution_result = await workflow_manager.execute_workflow(workflow_id, initial_data=initial_data)
    assert execution_result["status"] == "completed"
    assert "results" in execution_result
    # Check for anomaly flag and recommendation in the results
    found_anomaly = any(
        ("anomaly" in r and r["anomaly"] is True) or ("flag" in r and r["flag"] == "anomaly")
        for r in execution_result["results"]
    )
    found_recommendation = any(
        ("recommendation" in r) or ("advice" in r)
        for r in execution_result["results"]
    )
    assert found_anomaly, "Anomaly flag not found in workflow results."
    assert found_recommendation, "Recommendation not found in workflow results."

@pytest.mark.asyncio
async def test_workflow_dependency_execution(workflow_manager, setup_agents):
    """Test workflow execution with agent dependencies."""
    # Create agents with dependencies
    agent1 = ResearchTestAgent(agent_id="research_1")
    agent2 = DataProcessorTestAgent(agent_id="processor_1", dependencies=["research_1"])
    agent3 = ResearchTestAgent(agent_id="research_2", dependencies=["processor_1"])
    
    # Initialize agents
    await agent1.initialize()
    await agent2.initialize()
    await agent3.initialize()
    
    # Get capabilities
    agent1_capabilities = await agent1.get_capabilities()
    agent2_capabilities = await agent2.get_capabilities()
    agent3_capabilities = await agent3.get_capabilities()
    
    # Register agents
    await workflow_manager.registry.register_agent(agent1, agent1_capabilities)
    await workflow_manager.registry.register_agent(agent2, agent2_capabilities)
    await workflow_manager.registry.register_agent(agent3, agent3_capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Dependency Test Workflow",
        description="Test workflow with agent dependencies",
        required_capabilities=["test_research_agent", "test_data_processor"]
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Execute workflow
    await workflow_manager.execute_workflow(workflow_id)
    
    # Verify workflow status
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["status"] == WorkflowStatus.COMPLETED
    
    # Verify execution order through message history
    agent1_history = agent1.get_message_history()
    agent2_history = agent2.get_message_history()
    agent3_history = agent3.get_message_history()
    
    assert len(agent1_history) > 0
    assert len(agent2_history) > 0
    assert len(agent3_history) > 0
    
    assert agent2_history[0]["timestamp"] > agent1_history[0]["timestamp"]
    await asyncio.sleep(0.2)
    # Verify that agent3 executed after agent2
    assert agent3_history[0]["timestamp"] > agent2_history[0]["timestamp"]

@pytest.mark.asyncio
async def test_workflow_timeout_handling(workflow_manager, setup_agents):
    """Test workflow execution timeout handling."""
    # Create a slow agent
    class SlowTestAgent(ResearchTestAgent):
        async def process_message(self, message: AgentMessage) -> AgentMessage:
            await asyncio.sleep(10)  # Simulate slow processing
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender,
                content={"result": "slow"},
                timestamp=time.time(),
                message_type="response"
            )
    
    slow_agent = SlowTestAgent(agent_id="slow_agent")
    await slow_agent.initialize()
    agent_capabilities = await slow_agent.get_capabilities()
    await workflow_manager.registry.register_agent(slow_agent, agent_capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Timeout Test Workflow",
        description="Test workflow timeout handling",
        required_capabilities=["test_research_agent"]
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Execute workflow
    await workflow_manager.execute_workflow(workflow_id)
    
    # Verify workflow state
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["status"] == WorkflowStatus.FAILED

@pytest.mark.asyncio
async def test_workflow_error_recovery(workflow_manager, setup_agents):
    """Test workflow error recovery and reporting."""
    # Create an agent that fails
    class FailingTestAgent(ResearchTestAgent):
        async def process_message(self, message: AgentMessage) -> AgentMessage:
            raise Exception("Simulated failure")
    
    failing_agent = FailingTestAgent(agent_id="failing_agent")
    await failing_agent.initialize()
    agent_capabilities = await failing_agent.get_capabilities()
    await workflow_manager.registry.register_agent(failing_agent, agent_capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Error Recovery Test Workflow",
        description="Test workflow error recovery",
        required_capabilities=["test_research_agent"]
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Execute workflow
    await workflow_manager.execute_workflow(workflow_id)
    
    # Verify workflow state
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["status"] == WorkflowStatus.FAILED
    
    # Verify error tracking
    metrics = await workflow_manager.get_workflow_metrics(workflow_id)
    assert metrics["error_counts"]["failing_agent"] > 0

@pytest.mark.asyncio
async def test_transaction_atomicity(workflow_manager, agent_registry, test_capabilities):
    """Test that transactions are atomic."""
    # Create a workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow for atomic transaction testing",
        required_capabilities=test_capabilities,
        load_balancing_strategy="round_robin"
    )

    # Create an agent that will fail
    agent = TestAgent("test_agent", test_capabilities)
    agent.set_should_fail(True, max_fails=3)
    await agent.initialize()  # Initialize before getting capabilities
    agent_capabilities = await agent.get_capabilities()
    await agent_registry.register_agent(agent, agent_capabilities)

    # Try to assemble workflow - should fail and rollback
    result = await workflow_manager.assemble_workflow(workflow_id)
    assert result["status"] == "error"

    # Verify workflow state was not changed
    workflow = await workflow_manager.persistence.load_workflow(workflow_id)
    assert workflow["state"] == "created"

@pytest.mark.asyncio
async def test_retry_logic(workflow_manager, agent_registry, test_capabilities):
    """Test that retry logic works correctly."""
    # Create a workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow for retry logic testing",
        required_capabilities=test_capabilities,
        load_balancing_strategy="round_robin"
    )

    # Create an agent that will fail twice then succeed
    agent = TestAgent("test_agent", test_capabilities)
    agent.set_should_fail(True, max_fails=2)
    await agent.initialize()  # Initialize before getting capabilities
    agent_capabilities = await agent.get_capabilities()
    await agent_registry.register_agent(agent, agent_capabilities)

    # Execute workflow - should succeed after retries
    result = await workflow_manager.execute_workflow(workflow_id)
    assert result["status"] == "success"
    assert result["results"]["processed"] is True

@pytest.mark.asyncio
async def test_concurrent_transactions(workflow_manager, agent_registry, test_capabilities):
    """Test that concurrent transactions are handled correctly."""
    # Create multiple workflows
    workflow_ids = []
    for i in range(3):
        workflow_id = await workflow_manager.create_workflow(
            name=f"Test Workflow {i}",
            description=f"Test workflow {i} for concurrent transaction testing",
            required_capabilities=test_capabilities,
            load_balancing_strategy="round_robin"
        )
        workflow_ids.append(workflow_id)

    # Create an agent
    agent = TestAgent("test_agent", test_capabilities)
    await agent.initialize()  # Initialize before getting capabilities
    agent_capabilities = await agent.get_capabilities()
    await agent_registry.register_agent(agent, agent_capabilities)

    # Execute workflows concurrently
    async def execute_workflow(wf_id):
        return await workflow_manager.execute_workflow(wf_id)

    results = await asyncio.gather(
        *[execute_workflow(wf_id) for wf_id in workflow_ids]
    )

    # Verify all workflows completed successfully
    for result in results:
        assert result["status"] == "success"
        assert result["results"]["processed"] is True

@pytest.mark.asyncio
async def test_transaction_timeout(workflow_manager, agent_registry, test_capabilities):
    """Test that transactions timeout correctly."""
    # Create a workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow for timeout testing",
        required_capabilities=test_capabilities,
        load_balancing_strategy="round_robin"
    )

    # Create an agent that will take too long
    agent = TestAgent("test_agent", test_capabilities)
    async def slow_process(message):
        await asyncio.sleep(2)  # Simulate slow processing
        return AgentMessage(
            sender_id=agent.agent_id,
            recipient_id=message.sender,
            content={"processed": True},
            message_type="response"
        )
    agent.process_message = slow_process
    await agent.initialize()  # Initialize before getting capabilities
    agent_capabilities = await agent.get_capabilities()
    await agent_registry.register_agent(agent, agent_capabilities)

    # Try to execute workflow - should timeout
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(
            workflow_manager.execute_workflow(workflow_id),
            timeout=1.0
        ) 