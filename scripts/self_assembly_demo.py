import asyncio
from agents.core.workflow_manager import WorkflowManager
from agents.core.agent_registry import AgentRegistry
from agents.core.research_agent import ResearchAgent
from agents.core.data_processor_agent import DataProcessorAgent
from agents.core.sensor_agent import SensorAgent
from agents.core.feature_z_agent import FeatureZAgent
from agents.core.base_agent import AgentMessage
import time

async def run_self_assembly_demo():
    """Demonstrate enhanced self-assembly capabilities."""
    print("\n=== Self-Assembly Demo ===")
    
    # Initialize registry and workflow manager
    registry = AgentRegistry()
    workflow_manager = WorkflowManager(registry)
    await workflow_manager.initialize()
    
    # Create multiple agents with same capabilities
    research_agents = [
        ResearchAgent(f"research_agent_{i}", capabilities=["research"])
        for i in range(3)
    ]
    
    data_agents = [
        DataProcessorAgent(f"data_processor_{i}", capabilities=["data_processing"])
        for i in range(2)
    ]
    
    sensor_agents = [
        SensorAgent(f"sensor_agent_{i}", capabilities=["sensor_data"])
        for i in range(2)
    ]
    
    feature_agents = [
        FeatureZAgent(f"feature_agent_{i}", capabilities=["feature_processing"])
        for i in range(2)
    ]
    
    # Register all agents
    all_agents = research_agents + data_agents + sensor_agents + feature_agents
    for agent in all_agents:
        await registry.register_agent(agent)
        await agent.initialize()
        
    print("\n1. Testing Load Balancing")
    workflow_id = await workflow_manager.create_workflow(
        name="Load Balanced Analysis",
        description="Process data with load balancing",
        required_capabilities=["research", "data_processing"],
        max_agents_per_capability=2,
        load_balancing_strategy="round_robin"
    )
    
    # First assembly
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    print(f"First assembly agents: {assembly_result['agents']}")
    
    # Execute workflow
    await workflow_manager.execute_workflow(workflow_id, {"data": "test_data"})
    
    # Second assembly (should prefer less loaded agents)
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    print(f"Second assembly agents: {assembly_result['agents']}")
    
    print("\n2. Testing Performance-Based Selection")
    workflow_id = await workflow_manager.create_workflow(
        name="Performance Optimized Analysis",
        description="Process data with performance optimization",
        required_capabilities=["research"],
        max_agents_per_capability=1,
        load_balancing_strategy="performance"
    )
    
    # First assembly
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    print(f"Selected agent: {assembly_result['agents'][0]}")
    
    # Execute workflow multiple times to build performance metrics
    for _ in range(3):
        await workflow_manager.execute_workflow(workflow_id, {"data": "test_data"})
        time.sleep(0.1)  # Simulate different response times
        
    # Second assembly (should prefer best performing agent)
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    print(f"Selected agent: {assembly_result['agents'][0]}")
    
    print("\n3. Testing Workflow Validation")
    # Create a workflow with all capabilities
    workflow_id = await workflow_manager.create_workflow(
        name="Complete Analysis",
        description="Full data analysis workflow",
        required_capabilities=["research", "data_processing", "sensor_data", "feature_processing"],
        max_agents_per_capability=2
    )
    
    # Assemble and validate
    await workflow_manager.assemble_workflow(workflow_id)
    validation = await workflow_manager.validate_workflow(workflow_id)
    print(f"Workflow validation: {validation['is_valid']}")
    if not validation['is_valid']:
        print("Validation issues:")
        for issue in validation['issues']:
            print(f"- {issue['type']}: {issue.get('description', '')}")
            
    print("\n4. Testing Workflow Execution with Metrics")
    result = await workflow_manager.execute_workflow(workflow_id, {"data": "test_data"})
    print(f"Workflow execution status: {result['status']}")
    if result['status'] == 'completed':
        print("\nAgent performance metrics:")
        for agent_id, metrics in workflow_manager.agent_performance.items():
            print(f"\n{agent_id}:")
            print(f"- Response time: {metrics['response_time']:.3f}s")
            print(f"- Error count: {metrics['error_count']}")
            
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    asyncio.run(run_self_assembly_demo()) 