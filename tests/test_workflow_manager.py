import pytest
import pytest_asyncio
from typing import Dict, Any, Set
from agents.core.workflow_manager import WorkflowManager
from agents.core.base_agent import AgentMessage, BaseAgent
from agents.core.agent_registry import AgentRegistry
from tests.utils.test_agents import (
    ResearchTestAgent,
    DataProcessorTestAgent,
    SensorTestAgent,
    TestAgent
)
import asyncio
from agents.core.capability_types import Capability, CapabilityType
from datetime import datetime
import time

@pytest_asyncio.fixture(scope="function")
async def registry():
    """Create a fresh AgentRegistry instance for each test."""
    registry = AgentRegistry()
    await registry._auto_discover_agents()
    return registry

@pytest_asyncio.fixture(scope="function")
async def workflow_manager(registry):
    """Create a WorkflowManager instance with the registry."""
    manager = WorkflowManager(registry)
    await manager.initialize()
    return manager

@pytest_asyncio.fixture(scope="function")
async def setup_agents(registry):
    """Set up test agents with capabilities."""
    agents = {
        "test_research_agent": ResearchTestAgent(),
        "test_data_processor": DataProcessorTestAgent(),
        "test_sensor": SensorTestAgent(),
        "feature_z_agent": TestAgent(
            agent_id="feature_z_agent",
            agent_type="feature_processing",
            capabilities={"feature_processing"},
            default_response={"status": "feature_processed", "result": "Test feature"}
        )
    }
    
    # Register agents with their capabilities
    for agent in agents.values():
        await registry.register_agent(agent, agent.capabilities)
        await agent.initialize()
        
    yield agents
    
    # Cleanup after test
    for agent in agents.values():
        await registry.unregister_agent(agent.agent_id)
        agent.clear_history()

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
    agents = setup_agents
    
    # Verify agents are registered
    for agent_id, agent in agents.items():
        assert agent_id in registry.agents
        assert registry.agents[agent_id] == agent
        
    # Verify capabilities are registered
    for agent in agents.values():
        agent_capabilities = await registry.get_agent_capabilities(agent.agent_id)
        assert set(agent_capabilities) == agent.capabilities
        
    # Test capability-based agent lookup
    research_agents = await registry.get_agents_by_capability("test_research_agent")
    assert len(research_agents) == 1
    assert research_agents[0].agent_id == "test_research_agent"
    
    # Test capability update
    await registry.update_agent_capabilities("test_research_agent", {"research", "new_capability"})
    updated_capabilities = await registry.get_agent_capabilities("test_research_agent")
    assert set(updated_capabilities) == {"research", "new_capability"}
    
    # Test agent unregistration
    await registry.unregister_agent("test_research_agent")
    assert "test_research_agent" not in registry.agents
    research_agents = await registry.get_agents_by_capability("test_research_agent")
    assert len(research_agents) == 0

@pytest.mark.asyncio
async def test_workflow_creation(workflow_manager, test_capabilities):
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities=test_capabilities,
        max_agents_per_capability=2,
        load_balancing_strategy="round_robin"
    )
    
    assert workflow_id is not None
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["state"] == "created"

@pytest.mark.asyncio
async def test_workflow_assembly(workflow_manager, registry, test_capabilities):
    # Create agents with capabilities
    agent1 = TestAgent("agent1", {test_capabilities[0]})
    agent2 = TestAgent("agent2", {test_capabilities[1]})
    agent3 = TestAgent("agent3", {test_capabilities[2]})
    
    await registry.register_agent(agent1)
    await registry.register_agent(agent2)
    await registry.register_agent(agent3)
    
    # Create and assemble workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities=test_capabilities,
        max_agents_per_capability=1
    )
    
    result = await workflow_manager.assemble_workflow(workflow_id)
    assert result["status"] == "success"
    assert len(result["agents"]) == 3
    
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["state"] == "assembled"
    assert len(status["capability_assignments"]) == 3

@pytest.mark.asyncio
async def test_workflow_execution(workflow_manager, registry, test_capabilities):
    # Create agents with capabilities
    agent1 = TestAgent("agent1", {test_capabilities[0]})
    agent2 = TestAgent("agent2", {test_capabilities[1]})
    agent3 = TestAgent("agent3", {test_capabilities[2]})
    
    await registry.register_agent(agent1)
    await registry.register_agent(agent2)
    await registry.register_agent(agent3)
    
    # Create, assemble and execute workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities=test_capabilities,
        max_agents_per_capability=1
    )
    
    await workflow_manager.assemble_workflow(workflow_id)
    
    result = await workflow_manager.execute_workflow(
        workflow_id,
        initial_data={"test": "data"}
    )
    
    assert result["status"] == "success"
    assert result["results"]["processed"] is True
    assert result["results"]["data"]["test"] == "data"
    
    # Verify all agents processed the message
    assert len(agent1.processed_messages) == 1
    assert len(agent2.processed_messages) == 1
    assert len(agent3.processed_messages) == 1

@pytest.mark.asyncio
async def test_capability_change_handling(workflow_manager, registry, test_capabilities):
    # Create initial agent with one capability
    agent = TestAgent(
        "agent1",
        capabilities={Capability(CapabilityType.RESEARCH, "1.0")}
    )
    await registry.register_agent(agent, await agent.capabilities)
    
    # Create workflow requiring all capabilities
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities={
            Capability(CapabilityType.RESEARCH, "1.0"),
            Capability(CapabilityType.DATA_PROCESSING, "1.0"),
            Capability(CapabilityType.SENSOR_DATA, "1.0")
        },
        max_agents_per_capability=1
    )
    
    # Initial assembly should fail
    result = await workflow_manager.assemble_workflow(workflow_id)
    assert result["status"] == "error"
    assert "Missing required capabilities" in result["message"]
    
    # Update agent capabilities
    new_capabilities = {
        Capability(CapabilityType.RESEARCH, "1.0"),
        Capability(CapabilityType.DATA_PROCESSING, "1.0"),
        Capability(CapabilityType.SENSOR_DATA, "1.0")
    }
    await registry.update_agent_capabilities(agent.agent_id, new_capabilities)
    
    # Wait for notification processing
    await asyncio.sleep(0.1)
    
    # Verify workflow was reassembled
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["state"] == "assembled"
    assert len(status["agents"]) == 1

@pytest.mark.asyncio
async def test_load_balancing(workflow_manager, registry, test_capabilities):
    # Create multiple agents with same capability
    agent1 = TestAgent("agent1", {test_capabilities[0]})
    agent2 = TestAgent("agent2", {test_capabilities[0]})
    agent3 = TestAgent("agent3", {test_capabilities[0]})
    
    await registry.register_agent(agent1)
    await registry.register_agent(agent2)
    await registry.register_agent(agent3)
    
    # Create workflow with max_agents_per_capability=2
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities={test_capabilities[0]},
        max_agents_per_capability=2,
        load_balancing_strategy="least_loaded"
    )
    
    result = await workflow_manager.assemble_workflow(workflow_id)
    assert result["status"] == "success"
    assert len(result["agents"]) == 2

@pytest.mark.asyncio
async def test_workflow_metrics(workflow_manager, registry, test_capabilities):
    # Create agent and workflow
    agent = TestAgent("agent1", test_capabilities)
    await registry.register_agent(agent)
    
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities=test_capabilities,
        max_agents_per_capability=1
    )
    
    await workflow_manager.assemble_workflow(workflow_id)
    await workflow_manager.execute_workflow(workflow_id, {"test": "data"})
    
    # Get metrics
    metrics = await workflow_manager.get_workflow_metrics(workflow_id)
    assert metrics is not None
    assert "response_time" in metrics
    assert "error_count" in metrics

@pytest.mark.asyncio
async def test_concurrent_workflow_execution(workflow_manager, registry, test_capabilities):
    # Create agent with all capabilities
    agent = TestAgent("agent1", test_capabilities)
    await registry.register_agent(agent)
    
    # Create multiple workflows
    workflow_ids = []
    for i in range(3):
        workflow_id = await workflow_manager.create_workflow(
            name=f"Test Workflow {i}",
            description=f"Test workflow {i} description",
            required_capabilities=test_capabilities,
            max_agents_per_capability=1
        )
        workflow_ids.append(workflow_id)
    
    # Assemble all workflows
    for workflow_id in workflow_ids:
        await workflow_manager.assemble_workflow(workflow_id)
    
    # Execute workflows concurrently
    tasks = [
        workflow_manager.execute_workflow(wid, {"test": f"data_{i}"})
        for i, wid in enumerate(workflow_ids)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify all workflows completed successfully
    for result in results:
        assert result["status"] == "success"
        assert result["results"]["processed"] is True

@pytest.mark.asyncio
async def test_workflow_error_handling(workflow_manager, registry, test_capabilities):
    class ErrorAgent(TestAgent):
        async def process_message(self, message: AgentMessage) -> AgentMessage:
            raise Exception("Test error")
    
    # Create error agent
    agent = ErrorAgent("agent1", test_capabilities)
    await registry.register_agent(agent)
    
    # Create and execute workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow description",
        required_capabilities=test_capabilities,
        max_agents_per_capability=1
    )
    
    await workflow_manager.assemble_workflow(workflow_id)
    
    result = await workflow_manager.execute_workflow(workflow_id, {"test": "data"})
    assert result["status"] == "error"
    assert "Test error" in result["message"]
    
    # Verify workflow state
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["state"] == "error"

@pytest.mark.asyncio
async def test_workflow_validation(workflow_manager):
    """Test workflow validation."""
    workflow_id = await workflow_manager.create_workflow(
        name="Invalid Workflow",
        description="Workflow with missing capabilities",
        required_capabilities=["nonexistent_capability"]
    )
    
    validation = await workflow_manager.validate_workflow(workflow_id)
    assert not validation["is_valid"]
    assert any(issue["type"] == "missing_capability" for issue in validation["issues"])

@pytest.mark.asyncio
async def test_workflow_status_tracking(workflow_manager, setup_agents):
    """Test workflow status tracking."""
    workflow_id = await workflow_manager.create_workflow(
        name="Status Test Workflow",
        description="Test workflow status tracking",
        required_capabilities=["test_sensor", "test_data_processor"]
    )
    
    # Check initial status
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["state"] == "created"
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["state"] == "assembled"
    
    # Execute workflow
    await workflow_manager.execute_workflow(workflow_id, initial_data={})
    status = await workflow_manager.get_workflow_status(workflow_id)
    assert status["state"] == "completed"

@pytest.mark.asyncio
async def test_workflow_error_handling(workflow_manager, setup_agents):
    """Test workflow error handling."""
    workflow_id = await workflow_manager.create_workflow(
        name="Error Test Workflow",
        description="Test workflow error handling",
        required_capabilities=["test_sensor", "test_data_processor"]
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Execute with invalid data
    execution_result = await workflow_manager.execute_workflow(
        workflow_id,
        initial_data={"invalid": "data"}
    )
    
    assert execution_result["status"] == "error"
    assert "error" in execution_result
    assert "error_details" in execution_result

@pytest.mark.asyncio
async def test_workflow_cycle_detection(workflow_manager, setup_agents):
    """Test workflow cycle detection."""
    # Create agents with dependencies
    class CyclicAgent(TestAgent):
        def __init__(self, agent_id: str, dependencies: list):
            super().__init__(
                agent_id=agent_id,
                agent_type="cyclic",
                capabilities=["cyclic"],
                default_response={"status": "cyclic_processed"}
            )
            self.dependencies = dependencies
            
    agent1 = CyclicAgent("agent1", ["agent2"])
    agent2 = CyclicAgent("agent2", ["agent1"])
    
    await workflow_manager.registry.register_agent(agent1, agent1.capabilities)
    await workflow_manager.registry.register_agent(agent2, agent2.capabilities)
    
    workflow_id = await workflow_manager.create_workflow(
        name="Cyclic Workflow",
        description="Test cycle detection",
        required_capabilities=["cyclic"]
    )
    
    # Assemble workflow
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    assert assembly_result["status"] == "success"
    
    # Validate workflow
    validation = await workflow_manager.validate_workflow(workflow_id)
    assert not validation["is_valid"]
    assert any(issue["type"] == "workflow_cycle" for issue in validation["issues"])

@pytest.mark.asyncio
async def test_workflow_execution_metrics(workflow_manager, setup_agents):
    """Test workflow execution metrics tracking."""
    workflow_id = await workflow_manager.create_workflow(
        name="Metrics Workflow",
        description="Test metrics tracking",
        required_capabilities=["test_research_agent"]
    )
    
    # Assemble and execute workflow
    await workflow_manager.assemble_workflow(workflow_id)
    result = await workflow_manager.execute_workflow(workflow_id, {"data": "test"})
    
    assert result["status"] == "completed"
    assert len(result["results"]) > 0
    assert "response_time" in result["results"][0]
    
    # Check agent metrics
    agent_id = result["results"][0]["agent_id"]
    assert agent_id in workflow_manager.agent_performance
    assert "response_time" in workflow_manager.agent_performance[agent_id]
    assert "error_count" in workflow_manager.agent_performance[agent_id]

@pytest.mark.asyncio
async def test_dynamic_agent_registration(workflow_manager, registry):
    """Test that agents registered after workflow creation are discovered."""
    workflow_id = await workflow_manager.create_workflow(
        name="Dynamic Workflow",
        description="Test dynamic agent registration",
        required_capabilities=["test_research_agent"]
    )
    
    # First assembly should fail (no agents)
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    assert assembly_result["status"] == "error"
    
    # Register agent
    research_agent = ResearchTestAgent()
    await registry.register_agent(research_agent, research_agent.capabilities)
    await research_agent.initialize()
    
    # Second assembly should succeed
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    assert assembly_result["status"] == "success"
    assert len(assembly_result["agents"]) == 1
    assert "test_research_agent" in assembly_result["agents"]

@pytest.mark.asyncio
async def test_late_capability_change(workflow_manager, registry):
    """Test that agents gaining capabilities at runtime are discovered."""
    class MutableAgent(TestAgent):
        def __init__(self, agent_id, capabilities):
            super().__init__(agent_id, "dynamic_capability")
    agent = MutableAgent("mutable_agent", ["initial_capability"])
    await registry.register_agent(agent)
    # Create workflow requiring new capability
    workflow_id = await workflow_manager.create_workflow(
        name="Late Capability Workflow",
        description="Test late capability change",
        required_capabilities=["new_capability"]
    )
    # Should fail initially
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    print(f"[DEBUG] Capabilities before change: {registry.capabilities if hasattr(registry, 'capabilities') else registry.capability_map}")
    assert assembly_result["status"] == "error"
    # Add new capability to agent
    if hasattr(agent, 'capabilities'):
        agent.capabilities.add("new_capability")
    else:
        await registry.update_agent_capabilities(agent.agent_id, {"new_capability"})
        
    # Should succeed after capability change
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    assert assembly_result["status"] == "success"
    assert "mutable_agent" in assembly_result["agents"]

@pytest.mark.asyncio
async def test_no_agents_for_capability(workflow_manager):
    """Test workflow assembly fails gracefully when no agents are available for a capability."""
    workflow_id = await workflow_manager.create_workflow(
        name="No Agents Workflow",
        description="Test no agents for capability",
        required_capabilities=["nonexistent_capability"]
    )
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    print(f"[DEBUG] Assembly result for nonexistent capability: {assembly_result}")
    assert assembly_result["status"] == "error"
    assert "missing_capabilities" in assembly_result
    assert "nonexistent_capability" in assembly_result["missing_capabilities"]

@pytest.mark.asyncio
async def test_multiple_agents_per_capability(workflow_manager, registry):
    """Test that multiple agents with the same capability are all considered."""
    class MultiAgent(TestAgent):
        def __init__(self, agent_id):
            super().__init__(agent_id, "multi_capability")
    agent1 = MultiAgent("multi_agent_1")
    agent2 = MultiAgent("multi_agent_2")
    await registry.register_agent(agent1)
    await registry.register_agent(agent2)
    workflow_id = await workflow_manager.create_workflow(
        name="Multi-Agent Workflow",
        description="Test multiple agents per capability",
        required_capabilities=["multi_capability"],
        max_agents_per_capability=2
    )
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    print(f"[DEBUG] Agents for 'multi_capability': {assembly_result['agents']}")
    assert assembly_result["status"] == "success"
    assert len(assembly_result["agents"]) == 2
    assert "multi_agent_1" in assembly_result["agents"]
    assert "multi_agent_2" in assembly_result["agents"]

@pytest.mark.asyncio
async def test_registry_state_consistency(workflow_manager, registry):
    """Test that registry state remains consistent across workflow operations."""
    # Register initial agents
    agent1 = ResearchTestAgent(agent_id="research_1")
    agent2 = ResearchTestAgent(agent_id="research_2")
    await registry.register_agent(agent1, agent1.capabilities)
    await registry.register_agent(agent2, agent2.capabilities)
    
    # Create and assemble workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Consistency Test",
        description="Test registry state consistency",
        required_capabilities=["test_research_agent"]
    )
    
    # Verify initial state
    initial_agents = await registry.get_agents_by_capability("test_research_agent")
    assert len(initial_agents) == 2
    
    # Assemble workflow
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    assert assembly_result["status"] == "success"
    
    # Verify state after assembly
    post_assembly_agents = await registry.get_agents_by_capability("test_research_agent")
    assert len(post_assembly_agents) == 2
    assert set(a.agent_id for a in post_assembly_agents) == {"research_1", "research_2"}
    
    # Execute workflow
    await workflow_manager.execute_workflow(workflow_id, {"data": "test"})
    
    # Verify state after execution
    post_execution_agents = await registry.get_agents_by_capability("test_research_agent")
    assert len(post_execution_agents) == 2
    assert set(a.agent_id for a in post_execution_agents) == {"research_1", "research_2"}

@pytest.mark.asyncio
async def test_concurrent_registration_and_assembly(workflow_manager, registry):
    """Test handling of concurrent agent registration and workflow assembly."""
    # Create workflow first
    workflow_id = await workflow_manager.create_workflow(
        name="Concurrent Test",
        description="Test concurrent registration and assembly",
        required_capabilities=["test_research_agent", "test_data_processor"]
    )
    
    # Start assembly
    assembly_task = asyncio.create_task(workflow_manager.assemble_workflow(workflow_id))
    
    # Register agents during assembly
    agent1 = ResearchTestAgent(agent_id="research_1")
    agent2 = DataProcessorTestAgent(agent_id="processor_1")
    await registry.register_agent(agent1, agent1.capabilities)
    await registry.register_agent(agent2, agent2.capabilities)
    
    # Wait for assembly to complete
    assembly_result = await assembly_task
    
    # Verify results
    assert assembly_result["status"] == "success"
    assert len(assembly_result["agents"]) == 2
    assert "research_1" in assembly_result["agents"]
    assert "processor_1" in assembly_result["agents"]

@pytest.mark.asyncio
async def test_registry_recovery(workflow_manager, registry):
    """Test registry recovery after agent failures."""
    # Register agents
    agent1 = ResearchTestAgent(agent_id="research_1")
    agent2 = ResearchTestAgent(agent_id="research_2")
    await registry.register_agent(agent1, agent1.capabilities)
    await registry.register_agent(agent2, agent2.capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Recovery Test",
        description="Test registry recovery",
        required_capabilities=["test_research_agent"]
    )
    
    # Simulate agent failure
    await registry.unregister_agent("research_1")
    
    # Verify registry state
    agents = await registry.get_agents_by_capability("test_research_agent")
    assert len(agents) == 1
    assert agents[0].agent_id == "research_2"
    
    # Assemble workflow
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    assert assembly_result["status"] == "success"
    assert len(assembly_result["agents"]) == 1
    assert assembly_result["agents"][0] == "research_2"
    
    # Re-register failed agent
    await registry.register_agent(agent1, agent1.capabilities)
    
    # Verify registry recovery
    agents = await registry.get_agents_by_capability("test_research_agent")
    assert len(agents) == 2
    assert set(a.agent_id for a in agents) == {"research_1", "research_2"}

@pytest.mark.asyncio
async def test_capability_conflicts(workflow_manager, registry):
    """Test handling of conflicting capabilities between agents."""
    # Create agents with overlapping capabilities
    agent1 = TestAgent(
        agent_id="agent_1",
        agent_type="multi_capability",
        capabilities=["cap_a", "cap_b"],
        default_response={"status": "processed"}
    )
    agent2 = TestAgent(
        agent_id="agent_2",
        agent_type="multi_capability",
        capabilities=["cap_b", "cap_c"],
        default_response={"status": "processed"}
    )
    
    await registry.register_agent(agent1, agent1.capabilities)
    await registry.register_agent(agent2, agent2.capabilities)
    
    # Create workflow requiring conflicting capabilities
    workflow_id = await workflow_manager.create_workflow(
        name="Conflict Test",
        description="Test capability conflicts",
        required_capabilities=["cap_a", "cap_b", "cap_c"]
    )
    
    # Assemble workflow
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    assert assembly_result["status"] == "success"
    assert len(assembly_result["agents"]) == 2
    assert "agent_1" in assembly_result["agents"]
    assert "agent_2" in assembly_result["agents"]
    
    # Verify capability assignments
    workflow = await workflow_manager.get_workflow(workflow_id)
    assert "capability_assignments" in workflow
    assignments = workflow["capability_assignments"]
    assert assignments["cap_a"] == "agent_1"
    assert assignments["cap_b"] in ["agent_1", "agent_2"]
    assert assignments["cap_c"] == "agent_2"

@pytest.mark.asyncio
async def test_registry_persistence(workflow_manager, registry):
    """Test registry persistence across workflow operations."""
    # Register agents
    agent1 = ResearchTestAgent(agent_id="research_1")
    agent2 = DataProcessorTestAgent(agent_id="processor_1")
    await registry.register_agent(agent1, agent1.capabilities)
    await registry.register_agent(agent2, agent2.capabilities)
    
    # Create multiple workflows
    workflow_ids = []
    for i in range(3):
        workflow_id = await workflow_manager.create_workflow(
            name=f"Persistence Test {i}",
            description="Test registry persistence",
            required_capabilities=["test_research_agent", "test_data_processor"]
        )
        workflow_ids.append(workflow_id)
    
    # Assemble and execute workflows
    for workflow_id in workflow_ids:
        assembly_result = await workflow_manager.assemble_workflow(workflow_id)
        assert assembly_result["status"] == "success"
        assert len(assembly_result["agents"]) == 2
        
        await workflow_manager.execute_workflow(workflow_id, {"data": "test"})
    
    # Verify registry state remains consistent
    research_agents = await registry.get_agents_by_capability("test_research_agent")
    processor_agents = await registry.get_agents_by_capability("test_data_processor")
    
    assert len(research_agents) == 1
    assert len(processor_agents) == 1
    assert research_agents[0].agent_id == "research_1"
    assert processor_agents[0].agent_id == "processor_1"

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
    
    # Register agents
    await workflow_manager.registry.register_agent(agent1, agent1.capabilities)
    await workflow_manager.registry.register_agent(agent2, agent2.capabilities)
    await workflow_manager.registry.register_agent(agent3, agent3.capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Dependency Test Workflow",
        description="Test workflow with agent dependencies",
        required_capabilities=["test_research_agent", "test_data_processor"]
    )
    
    # Assemble workflow
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    assert assembly_result["status"] == "success"
    
    # Execute workflow
    execution_result = await workflow_manager.execute_workflow(
        workflow_id,
        initial_data={"data": "test"}
    )
    
    assert execution_result["status"] == "completed"
    assert "research_1" in execution_result["results"]
    assert "processor_1" in execution_result["results"]
    assert "research_2" in execution_result["results"]
    
    # Verify execution order through message history
    agent1_history = agent1.get_message_history()
    agent2_history = agent2.get_message_history()
    agent3_history = agent3.get_message_history()
    
    assert len(agent1_history) > 0
    assert len(agent2_history) > 0
    assert len(agent3_history) > 0
    
    # Verify that agent2 executed after agent1
    assert agent2_history[0]["timestamp"] > agent1_history[0]["timestamp"]
    # Verify that agent3 executed after agent2
    assert agent3_history[0]["timestamp"] > agent2_history[0]["timestamp"]

@pytest.mark.asyncio
async def test_workflow_timeout_handling(workflow_manager, setup_agents):
    """Test workflow execution timeout handling."""
    # Create a slow agent
    class SlowTestAgent(ResearchTestAgent):
        async def process(self, data: Dict) -> Dict:
            await asyncio.sleep(10)  # Simulate slow processing
            return {"result": "slow"}
    
    slow_agent = SlowTestAgent(agent_id="slow_agent")
    await workflow_manager.registry.register_agent(slow_agent, slow_agent.capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Timeout Test Workflow",
        description="Test workflow timeout handling",
        required_capabilities=["test_research_agent"]
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Execute workflow
    execution_result = await workflow_manager.execute_workflow(
        workflow_id,
        initial_data={"data": "test"}
    )
    
    assert execution_result["status"] == "error"
    assert "error" in execution_result
    assert "timeout" in execution_result["error"].lower()
    assert "error_details" in execution_result
    assert "agent_errors" in execution_result["error_details"]
    assert "slow_agent" in execution_result["error_details"]["agent_errors"]

@pytest.mark.asyncio
async def test_workflow_error_recovery(workflow_manager, setup_agents):
    """Test workflow error recovery and reporting."""
    # Create an agent that fails
    class FailingTestAgent(ResearchTestAgent):
        async def process(self, data: Dict) -> Dict:
            raise Exception("Simulated failure")
    
    failing_agent = FailingTestAgent(agent_id="failing_agent")
    await workflow_manager.registry.register_agent(failing_agent, failing_agent.capabilities)
    
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Error Recovery Test Workflow",
        description="Test workflow error recovery",
        required_capabilities=["test_research_agent"]
    )
    
    # Assemble workflow
    await workflow_manager.assemble_workflow(workflow_id)
    
    # Execute workflow
    execution_result = await workflow_manager.execute_workflow(
        workflow_id,
        initial_data={"data": "test"}
    )
    
    assert execution_result["status"] == "error"
    assert "error" in execution_result
    assert "error_details" in execution_result
    assert "agent_errors" in execution_result["error_details"]
    assert "failing_agent" in execution_result["error_details"]["agent_errors"]
    
    # Verify error tracking
    metrics = await workflow_manager.get_workflow_metrics(workflow_id)
    assert metrics["error_counts"]["failing_agent"] > 0
    
    # Verify workflow state
    workflow = await workflow_manager.get_workflow(workflow_id)
    assert workflow["state"] == "error"
    assert "error" in workflow
    assert "error_details" in workflow

@pytest.mark.asyncio
async def test_transaction_atomicity(workflow_manager, agent_registry, test_capabilities):
    """Test that transactions are atomic."""
    # Create a workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        required_capabilities=test_capabilities,
        load_balancing_strategy="round_robin"
    )

    # Create an agent that will fail
    agent = TestAgent("test_agent", test_capabilities)
    agent.set_should_fail(True, max_fails=3)
    await agent_registry.register_agent(agent)

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
        required_capabilities=test_capabilities,
        load_balancing_strategy="round_robin"
    )

    # Create an agent that will fail twice then succeed
    agent = TestAgent("test_agent", test_capabilities)
    agent.set_should_fail(True, max_fails=2)
    await agent_registry.register_agent(agent)

    # Execute workflow - should succeed after retries
    result = await workflow_manager.execute_workflow(
        workflow_id,
        initial_data={"test": "data"}
    )
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
            required_capabilities=test_capabilities,
            load_balancing_strategy="round_robin"
        )
        workflow_ids.append(workflow_id)

    # Create an agent
    agent = TestAgent("test_agent", test_capabilities)
    await agent_registry.register_agent(agent)

    # Execute workflows concurrently
    async def execute_workflow(wf_id):
        return await workflow_manager.execute_workflow(
            wf_id,
            initial_data={"test": "data"}
        )

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
        required_capabilities=test_capabilities,
        load_balancing_strategy="round_robin"
    )

    # Create an agent that will take too long
    agent = TestAgent("test_agent", test_capabilities)
    async def slow_process(message):
        await asyncio.sleep(2)  # Simulate slow processing
        return AgentMessage(
            sender=agent.agent_id,
            recipient=message.sender,
            content={"processed": True},
            message_type="response"
        )
    agent.process_message = slow_process
    await agent_registry.register_agent(agent)

    # Try to execute workflow - should timeout
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(
            workflow_manager.execute_workflow(
                workflow_id,
                initial_data={"test": "data"}
            ),
            timeout=1.0
        ) 