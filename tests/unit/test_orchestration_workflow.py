"""
Unit tests for the OrchestrationWorkflow system.
Tests all 7 steps of the workflow in isolation.
"""

import pytest
import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from agents.domain.orchestration_workflow import (
    OrchestrationWorkflow,
    execute_complete_workflow
)
from agents.core.message_types import AgentMessage


@pytest.fixture
async def mock_planner():
    """Create a mock planner agent."""
    planner = MagicMock()
    planner.agent_id = "test_planner"
    planner.knowledge_graph = AsyncMock()
    planner.knowledge_graph.add_triple = AsyncMock()
    planner.knowledge_graph.query_graph = AsyncMock(return_value=[])
    planner.process_message = AsyncMock(return_value=AgentMessage(
        sender_id="planner",
        recipient_id="orchestrator",
        content={"status": "success"},
        message_type="response"
    ))
    return planner


@pytest.fixture
async def mock_review_agent():
    """Create a mock review agent."""
    agent = MagicMock()
    agent.agent_id = "test_reviewer"
    agent.process_message = AsyncMock(return_value=AgentMessage(
        sender_id="reviewer",
        recipient_id="orchestrator",
        content={
            "status": "success",
            "recommendation": "approve",
            "commentary": "Plan looks good"
        },
        message_type="review_response"
    ))
    return agent


@pytest.fixture
async def mock_kg_manager():
    """Create a mock Knowledge Graph manager."""
    kg = AsyncMock()
    kg.add_triple = AsyncMock()
    kg.query_graph = AsyncMock(return_value=[])
    kg.initialize = AsyncMock()
    return kg


@pytest.fixture
async def mock_email_integration():
    """Create a mock email integration."""
    email = MagicMock()
    email.send_email = MagicMock(return_value={
        "status": "sent_simulated",
        "recipient": "test@example.com",
        "timestamp": datetime.now().isoformat()
    })
    return email


@pytest.fixture
async def sample_requirements_file(tmp_path):
    """Create a sample requirements file."""
    file_path = tmp_path / "requirements.txt"
    file_path.write_text("""
    Project: Test Workflow
    
    Objectives:
    - Objective 1
    - Objective 2
    
    Requirements:
    - Requirement 1
    - Requirement 2
    
    Deliverables:
    - Deliverable 1
    """)
    return str(file_path)


@pytest.fixture
async def orchestration_workflow(mock_planner, mock_review_agent, mock_kg_manager, mock_email_integration):
    """Create an orchestration workflow with mocked dependencies."""
    workflow = OrchestrationWorkflow(mock_planner, [mock_review_agent])
    workflow.kg_manager = mock_kg_manager
    workflow.email_integration = mock_email_integration
    await workflow.initialize()
    return workflow


class TestOrchestrationWorkflow:
    """Test suite for OrchestrationWorkflow class."""
    
    @pytest.mark.asyncio
    async def test_workflow_initialization(self, mock_planner, mock_review_agent):
        """Test workflow initialization."""
        workflow = OrchestrationWorkflow(mock_planner, [mock_review_agent])
        await workflow.initialize()
        
        assert workflow.planner == mock_planner
        assert len(workflow.review_agents) == 1
        assert workflow.workflow_id is None
        assert workflow.kg_manager is not None
    
    @pytest.mark.asyncio
    async def test_create_workflow_from_text(self, orchestration_workflow, sample_requirements_file):
        """Test Step 1: Create workflow from text file."""
        # Mock the plan creation (must be async)
        async def mock_create_and_store_plan(planner, theme, context):
            return {
                "id": "test_plan_id",
                "theme": "Test Workflow",
                "steps": [
                    {"step": 1, "action": "Test action", "agent": "test_agent", "output": "test_output"}
                ],
                "created_at": datetime.now().isoformat()
            }
        
        with patch('agents.domain.orchestration_workflow.create_and_store_plan', side_effect=mock_create_and_store_plan):
            result = await orchestration_workflow.create_workflow_from_text(
                sample_requirements_file,
                "test@example.com",
                "Test Workflow"
            )
        
        assert result["status"] == "created"
        assert result["next_step"] == "email_notification"
        assert "workflow_id" in result
        assert "plan" in result
        assert result["plan"]["id"] == "test_plan_id"
        assert orchestration_workflow.workflow_id is not None
    
    @pytest.mark.asyncio
    async def test_create_workflow_file_not_found(self, orchestration_workflow):
        """Test workflow creation with non-existent file."""
        result = await orchestration_workflow.create_workflow_from_text(
            "non_existent_file.txt",
            "test@example.com",
            "Test Workflow"
        )
        
        assert "error" in result
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_send_plan_for_review(self, orchestration_workflow):
        """Test Step 2: Send plan via email for review."""
        workflow_id = f"workflow_test_{uuid.uuid4().hex[:8]}"
        orchestration_workflow.workflow_id = workflow_id
        
        # Mock KG query to return plan URI
        orchestration_workflow.kg_manager.query_graph.return_value = [
            {"plan": f"http://example.org/plan/test_plan_id"}
        ]
        
        # Mock plan retrieval
        with patch('agents.domain.planner_kg_extension.retrieve_plan') as mock_retrieve:
            mock_retrieve.return_value = {
                "id": "test_plan_id",
                "theme": "Test Workflow",
                "created_at": datetime.now().isoformat(),
                "steps": [
                    {
                        "step": 1,
                        "action": "Test action",
                        "description": "Test description",
                        "agent": "test_agent",
                        "output": "test_output"
                    }
                ]
            }
            
            result = await orchestration_workflow.send_plan_for_review(
                workflow_id, "test@example.com"
            )
        
        assert result["workflow_id"] == workflow_id
        assert result["email_status"] == "sent_simulated"
        assert result["status"] == "pending_review"
        assert result["next_step"] == "visualize_in_kg"
        
        # Verify email was sent
        orchestration_workflow.email_integration.send_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_visualize_plan_in_kg(self, orchestration_workflow):
        """Test Step 3: Create KG visualization."""
        workflow_id = f"workflow_test_{uuid.uuid4().hex[:8]}"
        
        result = await orchestration_workflow.visualize_plan_in_kg(workflow_id)
        
        assert result["workflow_id"] == workflow_id
        assert "html_visualization" in result
        assert "sparql_queries" in result
        assert result["status"] == "visualized"
        assert result["next_step"] == "agent_review"
        
        # Verify KG triples were added
        assert orchestration_workflow.kg_manager.add_triple.called
    
    @pytest.mark.asyncio
    async def test_conduct_agent_review(self, orchestration_workflow):
        """Test Step 4: Multi-agent review."""
        workflow_id = f"workflow_test_{uuid.uuid4().hex[:8]}"
        
        # Mock KG query to return plan
        orchestration_workflow.kg_manager.query_graph.return_value = [
            {"plan": f"http://example.org/plan/test_plan_id"}
        ]
        
        # Mock plan retrieval
        with patch('agents.domain.planner_kg_extension.retrieve_plan') as mock_retrieve:
            mock_retrieve.return_value = {
                "id": "test_plan_id",
                "theme": "Test Workflow",
                "steps": []
            }
            
            result = await orchestration_workflow.conduct_agent_review(workflow_id)
        
        assert result["workflow_id"] == workflow_id
        assert "reviews" in result
        assert len(result["reviews"]) == 1
        assert result["reviews"][0]["recommendation"] == "approve"
        assert result["consensus"] == "approved"
        assert result["status"] == "reviewed"
        assert result["next_step"] == "validate_execution"
    
    @pytest.mark.asyncio
    async def test_validate_execution_readiness(self, orchestration_workflow):
        """Test Step 5: Validate execution readiness."""
        workflow_id = f"workflow_test_{uuid.uuid4().hex[:8]}"
        
        # Mock KG query
        orchestration_workflow.kg_manager.query_graph.return_value = [
            {"plan": f"http://example.org/plan/test_plan_id"}
        ]
        
        # Mock plan with valid structure
        with patch('agents.domain.planner_kg_extension.retrieve_plan') as mock_retrieve:
            mock_retrieve.return_value = {
                "id": "test_plan_id",
                "steps": [
                    {"step": 1, "agent": "test_agent", "output": "data"},
                    {"step": 2, "agent": "test_agent", "input": "data"}
                ]
            }
            
            # Mock agent existence check
            with patch.object(orchestration_workflow, '_check_agent_exists') as mock_check:
                mock_check.return_value = True
                
                result = await orchestration_workflow.validate_execution_readiness(workflow_id)
        
        assert result["workflow_id"] == workflow_id
        assert "validations" in result
        assert result["execution_ready"] == True
        assert result["status"] == "validated"
        assert result["next_step"] == "execute"
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, orchestration_workflow):
        """Test Step 6: Execute workflow with monitoring."""
        workflow_id = f"workflow_test_{uuid.uuid4().hex[:8]}"
        
        # Mock KG query - must return plan URI that matches plan_id extraction
        async def mock_query_graph(query):
            return [{"plan": "http://example.org/plan/test_plan_id"}]
        orchestration_workflow.kg_manager.query_graph = mock_query_graph
        
        # Mock plan retrieval (must be async) - patch where it's imported
        async def mock_retrieve_plan(planner, plan_id):
            plan = {
                "id": "test_plan_id",
                "steps": [
                    {"step": 1, "action": "Action 1", "agent": "agent1"},
                    {"step": 2, "action": "Action 2", "agent": "agent2"}
                ]
            }
            return plan
        
        with patch('agents.domain.orchestration_workflow.retrieve_plan', side_effect=mock_retrieve_plan):
            # Mock step execution (must be async)
            async def mock_execute_step(planner, plan_id, step_num):
                return {"status": "completed", "result": "success"}
            
            with patch('agents.domain.orchestration_workflow.execute_plan_step', side_effect=mock_execute_step):
                result = await orchestration_workflow.execute_workflow(workflow_id)
        
        assert result["workflow_id"] == workflow_id
        assert "execution_results" in result
        assert len(result["execution_results"]) == 2
        assert all(r["status"] == "completed" for r in result["execution_results"])
        assert result["status"] == "completed"
        assert result["next_step"] == "post_execution_analysis"
    
    @pytest.mark.asyncio
    async def test_conduct_post_execution_analysis(self, orchestration_workflow):
        """Test Step 7: Post-execution analysis."""
        workflow_id = f"workflow_test_{uuid.uuid4().hex[:8]}"
        
        # Mock execution data query
        orchestration_workflow.kg_manager.query_graph.return_value = [
            {"status": "completed", "step": "step1"},
            {"status": "completed", "step": "step2"}
        ]
        
        result = await orchestration_workflow.conduct_post_execution_analysis(workflow_id)
        
        assert result["workflow_id"] == workflow_id
        assert "analysis" in result
        assert result["analysis"]["total_steps"] == 2
        assert result["analysis"]["successful_steps"] == 2
        assert result["analysis"]["failed_steps"] == 0
        assert "agent_commentary" in result["analysis"]
        assert result["status"] == "analyzed"
        assert result["workflow_complete"] == True
    
    @pytest.mark.asyncio
    async def test_check_circular_dependencies(self, orchestration_workflow):
        """Test circular dependency detection."""
        # Plan with circular dependency
        plan_circular = {
            "steps": [
                {"step": 1, "output": "data_a", "input": "data_b"},
                {"step": 2, "output": "data_b", "input": "data_a"}
            ]
        }
        
        # Plan without circular dependency
        plan_valid = {
            "steps": [
                {"step": 1, "output": "data_a"},
                {"step": 2, "input": "data_a", "output": "data_b"}
            ]
        }
        
        assert orchestration_workflow._check_circular_dependencies(plan_circular) == True
        assert orchestration_workflow._check_circular_dependencies(plan_valid) == False
    
    @pytest.mark.asyncio
    async def test_format_plan_email(self, orchestration_workflow):
        """Test email formatting."""
        workflow_id = "test_workflow"
        plan = {
            "created_at": "2025-09-17T12:00:00",
            "theme": "Test Theme",
            "steps": [
                {
                    "step": 1,
                    "action": "Test Action",
                    "description": "Test Description",
                    "agent": "test_agent",
                    "output": "test_output"
                }
            ]
        }
        
        email_body = orchestration_workflow._format_plan_email(workflow_id, plan)
        
        assert "Workflow Plan Review Request" in email_body
        assert workflow_id in email_body
        assert "Test Theme" in email_body
        assert "Test Action" in email_body
        assert "APPROVED" in email_body
        assert "REJECTED" in email_body


class TestCompleteWorkflowIntegration:
    """Test the complete workflow execution."""
    
    @pytest.mark.asyncio
    async def test_execute_complete_workflow(self, tmp_path, mock_planner, mock_review_agent):
        """Test complete workflow from start to finish."""
        # Create requirements file
        requirements_file = tmp_path / "test_requirements.txt"
        requirements_file.write_text("Test requirements")
        
        # Mock all the necessary functions
        with patch('agents.domain.orchestration_workflow.OrchestrationWorkflow') as MockWorkflow:
            mock_instance = AsyncMock()
            MockWorkflow.return_value = mock_instance
            
            # Setup mock returns for each step
            mock_instance.initialize = AsyncMock()
            mock_instance.create_workflow_from_text = AsyncMock(return_value={
                "workflow_id": "test_id",
                "status": "created",
                "plan": {"id": "plan_id"}
            })
            mock_instance.send_plan_for_review = AsyncMock(return_value={
                "status": "pending_review"
            })
            mock_instance.visualize_plan_in_kg = AsyncMock(return_value={
                "status": "visualized"
            })
            mock_instance.conduct_agent_review = AsyncMock(return_value={
                "consensus": "approved"
            })
            mock_instance.validate_execution_readiness = AsyncMock(return_value={
                "execution_ready": True
            })
            mock_instance.execute_workflow = AsyncMock(return_value={
                "status": "completed"
            })
            mock_instance.conduct_post_execution_analysis = AsyncMock(return_value={
                "status": "analyzed"
            })
            
            # Execute complete workflow
            from agents.domain.orchestration_workflow import execute_complete_workflow
            results = await execute_complete_workflow(
                str(requirements_file),
                "test@example.com",
                mock_planner,
                [mock_review_agent]
            )
        
        # Verify all steps were executed
        assert "creation" in results
        assert "email" in results
        assert "visualization" in results
        assert "review" in results
        assert "validation" in results
        assert "execution" in results
        assert "analysis" in results


class TestErrorHandling:
    """Test error handling in the workflow."""
    
    @pytest.mark.asyncio
    async def test_workflow_handles_agent_failure(self, orchestration_workflow):
        """Test workflow handles agent failures gracefully."""
        workflow_id = "test_workflow"
        
        # Mock a failing review agent
        failing_agent = MagicMock()
        failing_agent.agent_id = "failing_agent"
        failing_agent.process_message = AsyncMock(side_effect=Exception("Agent failed"))
        orchestration_workflow.review_agents = [failing_agent]
        
        # Mock KG query
        orchestration_workflow.kg_manager.query_graph.return_value = [
            {"plan": "http://example.org/plan/test_plan"}
        ]
        
        with patch('agents.domain.planner_kg_extension.retrieve_plan') as mock_retrieve:
            mock_retrieve.return_value = {"id": "test_plan", "steps": []}
            
            # Should handle the error and continue
            result = await orchestration_workflow.conduct_agent_review(workflow_id)
        
        assert result["workflow_id"] == workflow_id
        assert len(result["reviews"]) == 1
        assert result["reviews"][0]["review"]["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_workflow_handles_execution_failure(self, orchestration_workflow):
        """Test workflow handles execution failures."""
        workflow_id = "test_workflow"
        
        # Mock KG query
        async def mock_query_graph(query):
            return [{"plan": "http://example.org/plan/test_plan"}]
        orchestration_workflow.kg_manager.query_graph = mock_query_graph
        
        # Mock plan retrieval (must be async)
        async def mock_retrieve_plan(planner, plan_id):
            return {
                "id": "test_plan",
                "steps": [{"step": 1, "action": "Failing action"}]
            }
        
        with patch('agents.domain.orchestration_workflow.retrieve_plan', side_effect=mock_retrieve_plan):
            # Mock step execution failure (must be async)
            async def mock_execute_step(planner, plan_id, step_num):
                raise Exception("Execution failed")
            
            with patch('agents.domain.orchestration_workflow.execute_plan_step', side_effect=mock_execute_step):
                result = await orchestration_workflow.execute_workflow(workflow_id)
        
        assert result["workflow_id"] == workflow_id
        assert len(result["execution_results"]) == 1
        assert result["execution_results"][0]["status"] == "failed"
        assert "Execution failed" in result["execution_results"][0]["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
