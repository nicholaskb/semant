"""Tests for KG tools and orchestration functionality."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from agents.tools.kg_tools import KGTools, KGToolRegistry
from agents.domain.kg_orchestrator_agent import KGOrchestratorAgent
from agents.core.message_types import AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager


@pytest.fixture
async def kg_manager():
    """Create a test KG manager."""
    kg = KnowledgeGraphManager(persistent_storage=False)
    await kg.initialize()
    return kg


@pytest.fixture
async def kg_tools(kg_manager):
    """Create KG tools instance."""
    return KGTools(kg_manager, "test_agent")


@pytest.fixture
async def orchestrator_agent(kg_manager):
    """Create orchestrator agent."""
    agent = KGOrchestratorAgent("test_orchestrator")
    agent.knowledge_graph = kg_manager
    await agent.initialize()
    return agent


class TestKGTools:
    """Test KG tools functionality."""
    
    async def test_create_task_node(self, kg_tools):
        """Test creating a task node."""
        task_id = await kg_tools.create_task_node(
            task_name="Test Task",
            task_type="testing",
            description="A test task",
            priority="high",
            metadata={"test": True}
        )
        
        assert task_id.startswith("http://example.org/task/")
        
        # Verify task was created
        query = f"""
        PREFIX core: <http://example.org/core#>
        SELECT ?name ?type ?priority WHERE {{
            <{task_id}> core:taskName ?name ;
                       core:taskType ?type ;
                       core:priority ?priority .
        }}
        """
        
        results = await kg_tools.kg.query_graph(query)
        assert len(results) == 1
        assert results[0]['name'] == "Test Task"
        assert results[0]['type'] == "testing"
        assert results[0]['priority'] == "high"
        
    async def test_create_workflow_node(self, kg_tools):
        """Test creating a workflow with steps."""
        steps = [
            {
                "name": "Step 1",
                "type": "process",
                "description": "First step"
            },
            {
                "name": "Step 2",
                "type": "analyze",
                "description": "Second step"
            }
        ]
        
        workflow_id = await kg_tools.create_workflow_node(
            workflow_name="Test Workflow",
            workflow_type="sequential",
            steps=steps
        )
        
        assert workflow_id.startswith("http://example.org/workflow/")
        
        # Verify workflow and tasks were created
        query = f"""
        PREFIX core: <http://example.org/core#>
        SELECT ?task ?name WHERE {{
            <{workflow_id}> core:hasTask ?task .
            ?task core:taskName ?name .
        }}
        ORDER BY ?name
        """
        
        results = await kg_tools.kg.query_graph(query)
        assert len(results) == 2
        assert results[0]['name'] == "Step 1"
        assert results[1]['name'] == "Step 2"
        
    async def test_query_available_tasks(self, kg_tools):
        """Test querying for available tasks."""
        # Create some test tasks
        task1 = await kg_tools.create_task_node(
            "Task 1", "type_a", "Description 1", "high"
        )
        task2 = await kg_tools.create_task_node(
            "Task 2", "type_b", "Description 2", "low"
        )
        
        # Query all available tasks
        tasks = await kg_tools.query_available_tasks()
        assert len(tasks) >= 2
        
        # Query by type
        type_a_tasks = await kg_tools.query_available_tasks(task_types=["type_a"])
        assert any(t['task'] == task1 for t in type_a_tasks)
        
        # Query by priority
        high_priority = await kg_tools.query_available_tasks(priority="high")
        assert any(t['task'] == task1 for t in high_priority)
        
    async def test_claim_and_update_task(self, kg_tools):
        """Test claiming and updating task status."""
        # Create a task
        task_id = await kg_tools.create_task_node(
            "Claimable Task", "process", "Test claiming"
        )
        
        # Claim it
        claimed = await kg_tools.claim_task(task_id)
        assert claimed is True
        
        # Try to claim again (should fail)
        claimed_again = await kg_tools.claim_task(task_id)
        assert claimed_again is False
        
        # Update status to completed
        await kg_tools.update_task_status(
            task_id,
            "completed",
            result={"output": "Task completed successfully"}
        )
        
        # Verify status
        query = f"""
        PREFIX core: <http://example.org/core#>
        SELECT ?status ?result WHERE {{
            <{task_id}> core:status ?status .
            OPTIONAL {{ <{task_id}> core:result ?result }}
        }}
        """
        
        results = await kg_tools.kg.query_graph(query)
        assert results[0]['status'] == "completed"
        assert "successfully" in results[0]['result']
        
    async def test_agent_discovery(self, kg_tools):
        """Test discovering other agents."""
        # Create test agents
        agent1 = await kg_tools.create_agent_node(
            "Agent 1", "worker", ["cap1", "cap2"]
        )
        agent2 = await kg_tools.create_agent_node(
            "Agent 2", "analyzer", ["cap2", "cap3"]
        )
        
        # Discover all agents
        agents = await kg_tools.discover_agents()
        assert len(agents) >= 2
        
        # Discover by capability
        cap2_agents = await kg_tools.discover_agents(capabilities=["cap2"])
        agent_ids = [a['agent'] for a in cap2_agents]
        assert agent1 in agent_ids
        assert agent2 in agent_ids
        
    async def test_message_broadcasting(self, kg_tools):
        """Test message broadcasting and querying."""
        # Create an agent node with cap1 capability so messages can be queried
        agent_id = await kg_tools.create_agent_node(
            "Test Agent", "test", ["cap1"]
        )
        # Update kg_tools to use the created agent ID
        kg_tools.agent_id = agent_id
        
        # Broadcast a message
        msg_id = await kg_tools.broadcast_message(
            "test_notification",
            {"content": "Test message"},
            target_capabilities=["cap1"]
        )
        
        assert msg_id.startswith("http://example.org/message/")
        
        # Query messages
        messages = await kg_tools.query_messages(
            message_types=["test_notification"]
        )
        
        assert len(messages) >= 1
        assert messages[0]['content']['content'] == "Test message"
        
        # Mark as read
        await kg_tools.mark_message_read(msg_id)
        
        # Query unread messages (should be empty)
        unread = await kg_tools.query_messages(
            message_types=["test_notification"],
            status="unread"
        )
        assert len(unread) == 0
        
    async def test_workflow_status(self, kg_tools):
        """Test querying workflow status."""
        # Create workflow with tasks
        workflow_id = await kg_tools.create_workflow_node(
            "Status Test Workflow",
            "sequential",
            [
                {"name": "Task A", "type": "process", "description": "First"},
                {"name": "Task B", "type": "analyze", "description": "Second"}
            ]
        )
        
        # Get initial status
        status = await kg_tools.query_workflow_status(workflow_id)
        assert status['workflow_id'] == workflow_id
        assert status['status'] == 'in_progress'  # Tasks are pending, which means in_progress
        assert status['total_tasks'] == 2
        assert status['completed_tasks'] == 0
        
        # Complete one task
        task_a = status['tasks'][0]['task']
        await kg_tools.claim_task(task_a)
        await kg_tools.update_task_status(task_a, "completed")
        
        # Check status again
        status = await kg_tools.query_workflow_status(workflow_id)
        assert status['status'] == 'in_progress'
        assert status['completed_tasks'] == 1


class TestKGOrchestratorAgent:
    """Test the KG orchestrator agent."""
    
    async def test_create_task_message(self, orchestrator_agent):
        """Test handling create_task message."""
        msg = AgentMessage(
            sender_id="test",
            recipient_id=orchestrator_agent.agent_id,
            message_type="create_task",
            content={
                "name": "Test Task",
                "type": "testing",
                "description": "Test task creation",
                "priority": "medium"
            }
        )
        
        response = await orchestrator_agent.process_message(msg)
        assert response.message_type == "task_created"
        assert "task_id" in response.content
        assert response.content['status'] == "pending"
        
    async def test_create_workflow_message(self, orchestrator_agent):
        """Test handling create_workflow message."""
        msg = AgentMessage(
            sender_id="test",
            recipient_id=orchestrator_agent.agent_id,
            message_type="create_workflow",
            content={
                "name": "Test Workflow",
                "type": "parallel",
                "steps": [
                    {"name": "Step 1", "type": "process"},
                    {"name": "Step 2", "type": "analyze"}
                ]
            }
        )
        
        response = await orchestrator_agent.process_message(msg)
        assert response.message_type == "workflow_created"
        assert "workflow_id" in response.content
        
    async def test_orchestrate_agents_discover(self, orchestrator_agent):
        """Test agent discovery through orchestrator."""
        # Create test agent first
        await orchestrator_agent.kg_tools.create_agent_node(
            "Test Worker", "worker", ["test_capability"]
        )
        
        msg = AgentMessage(
            sender_id="test",
            recipient_id=orchestrator_agent.agent_id,
            message_type="orchestrate_agents",
            content={
                "operation": "discover",
                "capabilities": ["test_capability"]
            }
        )
        
        response = await orchestrator_agent.process_message(msg)
        if response.message_type == "error":
            # Debug: print the error to understand what's failing
            print(f"Error response: {response.content}")
        assert response.message_type == "agents_discovered", f"Expected 'agents_discovered', got '{response.message_type}'. Error: {response.content.get('error', 'Unknown')}"
        assert len(response.content['agents']) >= 1
        
    async def test_kg_tool_invocation(self, orchestrator_agent):
        """Test direct KG tool invocation."""
        msg = AgentMessage(
            sender_id="test",
            recipient_id=orchestrator_agent.agent_id,
            message_type="kg_tool",
            content={
                "tool": "create_task_node",
                "parameters": {
                    "task_name": "Tool Test Task",
                    "task_type": "testing",
                    "description": "Created via tool invocation"
                }
            }
        )
        
        response = await orchestrator_agent.process_message(msg)
        assert response.message_type == "kg_tool_result"
        assert response.content['success'] is True
        assert response.content['tool'] == "create_task_node"
        assert response.content['result'].startswith("http://example.org/task/")
        
    async def test_unknown_message_handling(self, orchestrator_agent):
        """Test handling of unknown message types."""
        msg = AgentMessage(
            sender_id="test",
            recipient_id=orchestrator_agent.agent_id,
            message_type="unknown_type",
            content={}
        )
        
        response = await orchestrator_agent.process_message(msg)
        assert response.message_type == "error"
        assert "Unknown message type" in response.content['error']
        assert "available_types" in response.content
        
    async def test_create_and_execute_plan(self, orchestrator_agent):
        """Test high-level plan creation and execution."""
        plan_steps = [
            {
                "name": "Data Collection",
                "type": "collect",
                "description": "Gather required data"
            },
            {
                "name": "Analysis",
                "type": "analyze",
                "description": "Analyze collected data"
            }
        ]
        
        workflow_id = await orchestrator_agent.create_and_execute_plan(
            "Test Analysis Plan",
            plan_steps
        )
        
        assert workflow_id.startswith("http://example.org/workflow/")
        
        # Verify workflow was created
        status = await orchestrator_agent.kg_tools.query_workflow_status(workflow_id)
        assert status['total_tasks'] == 2
        

class TestKGToolRegistry:
    """Test the KG tool registry."""
    
    def test_get_tool_descriptions(self):
        """Test getting tool descriptions."""
        descriptions = KGToolRegistry.get_tool_descriptions()
        
        # Check some key tools are present
        assert "create_task_node" in descriptions
        assert "query_available_tasks" in descriptions
        assert "discover_agents" in descriptions
        
        # Check description structure
        task_desc = descriptions["create_task_node"]
        assert "description" in task_desc
        assert "parameters" in task_desc
        assert "returns" in task_desc
        
        # Check parameter details
        assert "task_name" in task_desc["parameters"]
        assert "priority" in task_desc["parameters"]
