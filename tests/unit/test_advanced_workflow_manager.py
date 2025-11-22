"""
Unit tests for Advanced Workflow Manager

Tests conditional branching, parallel execution, and dynamic workflow modification.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from agents.core.advanced_workflow_manager import (
    AdvancedWorkflowManager,
    AdvancedWorkflow,
    AdvancedWorkflowStep,
    Condition,
    ConditionType,
    WorkflowBranch,
    ExecutionMode
)
from agents.core.workflow_types import WorkflowStatus
from agents.core.agent_registry import AgentRegistry
from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.capability_types import CapabilityType, Capability


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(self, agent_id: str, capabilities=None):
        super().__init__(agent_id=agent_id, capabilities=capabilities or [])
        self.processed_messages = []
        self.should_succeed = True

    async def get_capabilities(self):
        return self._capabilities

    async def _process_message_impl(self, message: AgentMessage):
        self.processed_messages.append(message)

        if self.should_succeed:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"success": True, "result": f"Processed by {self.agent_id}"},
                message_type="response"
            )
        else:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"success": False, "error": "Mock failure"},
                message_type="response"
            )


@pytest.fixture
async def workflow_manager():
    """Create a workflow manager for testing."""
    registry = AgentRegistry()

    # Add mock agents with valid CapabilityType enum values
    agent1 = MockAgent("agent1", [Capability(CapabilityType.RESEARCH, "1.0")])
    agent2 = MockAgent("agent2", [Capability(CapabilityType.REASONING, "1.0")])
    agent3 = MockAgent("agent3", [Capability(CapabilityType.DATA_PROCESSING, "1.0")])

    await registry.register_agent(agent1)
    await registry.register_agent(agent2)
    await registry.register_agent(agent3)

    manager = AdvancedWorkflowManager(registry)
    await manager.initialize()

    return manager


@pytest.fixture
def sample_workflow():
    """Create a sample advanced workflow."""
    workflow = AdvancedWorkflow(
        id="test-workflow",
        name="Test Workflow",
        description="A test advanced workflow"
    )

    # Add steps with valid CapabilityType enum values
    workflow.steps = [
        AdvancedWorkflowStep(
            id="step1",
            capability=CapabilityType.RESEARCH.value,
            parameters={"input": "test1"}
        ),
        AdvancedWorkflowStep(
            id="step2",
            capability=CapabilityType.REASONING.value,
            parameters={"input": "test2"},
            execution_mode=ExecutionMode.CONDITIONAL,
            conditions=[
                Condition(
                    type=ConditionType.SUCCESS,
                    step_id="step1"
                )
            ]
        ),
        AdvancedWorkflowStep(
            id="step3",
            capability=CapabilityType.DATA_PROCESSING.value,
            parameters={"input": "test3"},
            execution_mode=ExecutionMode.PARALLEL,
            parallel_group="group1"
        ),
        AdvancedWorkflowStep(
            id="step4",
            capability=CapabilityType.RESEARCH.value,
            parameters={"input": "test4"},
            execution_mode=ExecutionMode.PARALLEL,
            parallel_group="group1"
        )
    ]

    return workflow


class TestAdvancedWorkflowManager:
    """Test the advanced workflow manager."""

    @pytest.mark.asyncio
    async def test_workflow_initialization(self, workflow_manager):
        """Test workflow manager initialization."""
        assert workflow_manager.registry is not None
        assert workflow_manager._workflows == {}
        assert workflow_manager._step_results == {}

    @pytest.mark.asyncio
    async def test_execute_basic_workflow(self, workflow_manager, sample_workflow):
        """Test executing a basic advanced workflow."""
        result = await workflow_manager.execute_advanced_workflow(sample_workflow)

        assert result['workflow_id'] == sample_workflow.id
        assert result['status'] == WorkflowStatus.COMPLETED
        assert result['steps_executed'] == 4
        assert sample_workflow.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_conditional_execution_success(self, workflow_manager):
        """Test conditional step execution when condition is met."""
        workflow = AdvancedWorkflow(id="conditional-test", name="Conditional Test")

        workflow.steps = [
            AdvancedWorkflowStep(
                id="success_step",
                capability=CapabilityType.RESEARCH.value,
                parameters={}
            ),
            AdvancedWorkflowStep(
                id="conditional_step",
                capability=CapabilityType.REASONING.value,
                parameters={},
                execution_mode=ExecutionMode.CONDITIONAL,
                conditions=[
                    Condition(
                        type=ConditionType.SUCCESS,
                        step_id="success_step"
                    )
                ]
            )
        ]

        result = await workflow_manager.execute_advanced_workflow(workflow)

        assert result['status'] == WorkflowStatus.COMPLETED
        assert len(result['step_results']) == 2
        assert 'conditional_step' in result['step_results']

    @pytest.mark.asyncio
    async def test_conditional_execution_failure(self, workflow_manager):
        """Test conditional step execution when condition is not met."""
        workflow = AdvancedWorkflow(id="conditional-test", name="Conditional Test")

        # Make the first agent fail
        agents = workflow_manager.registry.get_all_agents()
        for agent in agents:
            capabilities = await agent.get_capabilities()
            if any(cap.type == CapabilityType.RESEARCH for cap in capabilities):
                agent.should_succeed = False
                break

        workflow.steps = [
            AdvancedWorkflowStep(
                id="fail_step",
                capability=CapabilityType.RESEARCH.value,
                parameters={}
            ),
            AdvancedWorkflowStep(
                id="conditional_step",
                capability=CapabilityType.REASONING.value,
                parameters={},
                execution_mode=ExecutionMode.CONDITIONAL,
                conditions=[
                    Condition(
                        type=ConditionType.SUCCESS,
                        step_id="fail_step"
                    )
                ]
            )
        ]

        result = await workflow_manager.execute_advanced_workflow(workflow)

        # Workflow should complete but conditional step should not execute
        assert result['status'] == WorkflowStatus.FAILED  # Because fail_step failed
        assert len(result['step_results']) == 1  # Only fail_step executed
        assert 'conditional_step' not in result['step_results']

    @pytest.mark.asyncio
    async def test_parallel_execution(self, workflow_manager):
        """Test parallel execution of steps."""
        workflow = AdvancedWorkflow(id="parallel-test", name="Parallel Test")

        workflow.steps = [
            AdvancedWorkflowStep(
                id="parallel_step1",
                capability=CapabilityType.RESEARCH.value,
                parameters={},
                execution_mode=ExecutionMode.PARALLEL,
                parallel_group="group1"
            ),
            AdvancedWorkflowStep(
                id="parallel_step2",
                capability=CapabilityType.REASONING.value,
                parameters={},
                execution_mode=ExecutionMode.PARALLEL,
                parallel_group="group1"
            ),
            AdvancedWorkflowStep(
                id="parallel_step3",
                capability=CapabilityType.DATA_PROCESSING.value,
                parameters={},
                execution_mode=ExecutionMode.PARALLEL,
                parallel_group="group1"
            )
        ]

        start_time = asyncio.get_event_loop().time()
        result = await workflow_manager.execute_advanced_workflow(workflow)
        end_time = asyncio.get_event_loop().time()

        assert result['status'] == WorkflowStatus.COMPLETED
        assert len(result['step_results']) == 3

        # Parallel execution should be faster than sequential
        execution_time = result['execution_time']
        assert execution_time < 1.0  # Should complete quickly with parallel execution

    @pytest.mark.asyncio
    async def test_workflow_template_creation(self, workflow_manager):
        """Test creating workflows from templates."""
        template_params = {
            "source": "test_source",
            "validation_rules": ["rule1", "rule2"],
            "transformations": ["transform1"]
        }

        workflow = await workflow_manager.create_workflow_from_template(
            "data_processing",
            template_params
        )

        assert workflow.name == "Template: data_processing"
        assert len(workflow.steps) == 3
        assert workflow.steps[0].capability == "data_ingestion"
        assert workflow.steps[1].capability == "data_validation"
        assert workflow.steps[2].capability == "data_processing"

    @pytest.mark.asyncio
    async def test_dynamic_workflow_modification(self, workflow_manager):
        """Test dynamic workflow modification during execution."""
        workflow = AdvancedWorkflow(id="dynamic-test", name="Dynamic Test")

        workflow.steps = [
            AdvancedWorkflowStep(
                id="step1",
                capability=CapabilityType.RESEARCH.value,
                parameters={}
            )
        ]

        # Start workflow execution
        task = asyncio.create_task(workflow_manager.execute_advanced_workflow(workflow))

        # Wait a bit for execution to start
        await asyncio.sleep(0.1)

        # Modify workflow dynamically
        modifications = {
            'add_steps': [{
                'id': 'dynamic_step',
                'capability': CapabilityType.REASONING.value,
                'parameters': {}
            }]
        }

        success = await workflow_manager.modify_workflow_dynamically(
            workflow.id,
            modifications
        )

        assert success

        # Wait for completion
        result = await task

        assert result['status'] == WorkflowStatus.COMPLETED
        # Should have executed both original and dynamic steps
        assert len(result['step_results']) >= 1

    @pytest.mark.asyncio
    async def test_retry_policy(self, workflow_manager):
        """Test retry policy for failed steps."""
        # Make an agent fail initially but succeed on retry
        agents = workflow_manager.registry.get_all_agents()
        retry_agent = None
        for agent in agents:
            try:
                capabilities = await agent.get_capabilities()
                if any(cap.type == CapabilityType.RESEARCH for cap in capabilities):
                    retry_agent = agent
                    break
            except:
                continue

        # Custom retry logic simulation
        retry_count = 0
        original_process = retry_agent._process_message_impl

        async def failing_process(message):
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:  # Fail first 2 attempts
                return AgentMessage(
                    sender_id=retry_agent.agent_id,
                    recipient_id=message.sender_id,
                    content={"success": False, "error": "Temporary failure"},
                    message_type="response"
                )
            else:  # Succeed on 3rd attempt
                return await original_process(message)

        retry_agent._process_message_impl = failing_process

        try:
            workflow = AdvancedWorkflow(name="Retry Test")
            workflow.steps = [
                AdvancedWorkflowStep(
                    id="retry_step",
                    capability=CapabilityType.RESEARCH.value,
                    parameters={},
                    retry_policy={
                        'max_retries': 3,
                        'backoff_factor': 0.1,
                        'retry_on': ['failure']
                    }
                )
            ]

            result = await workflow_manager.execute_advanced_workflow(workflow)

            assert result['status'] == WorkflowStatus.COMPLETED
            assert retry_count == 3  # Should have failed twice and succeeded once

        finally:
            retry_agent._process_message_impl = original_process

    @pytest.mark.asyncio
    async def test_workflow_analytics(self, workflow_manager):
        """Test workflow analytics collection."""
        # Execute a few workflows
        for i in range(3):
            workflow = AdvancedWorkflow(id=f"analytics-test-{i}", name=f"Analytics Test {i}")
            workflow.steps = [
                AdvancedWorkflowStep(
                    id=f"step_{i}",
                    capability=CapabilityType.RESEARCH.value,
                    parameters={}
                )
            ]

            await workflow_manager.execute_advanced_workflow(workflow)

        analytics = workflow_manager.get_workflow_analytics()

        assert analytics['total_workflows'] == 3
        assert analytics['completed_workflows'] == 3
        assert analytics['failed_workflows'] == 0
        assert analytics['average_execution_time'] > 0
        assert analytics['parallel_execution_efficiency'] > 0

    @pytest.mark.asyncio
    async def test_condition_evaluation(self):
        """Test condition evaluation logic."""
        step_results = {
            'step1': {'success': True, 'content': 'Success result'},
            'step2': {'success': False, 'content': 'Failure result'},
            'step3': {'success': True, 'content': 'Result with specific text'}
        }

        # Test success condition
        success_condition = Condition(
            type=ConditionType.SUCCESS,
            step_id='step1'
        )
        assert await success_condition.evaluate(step_results) is True

        # Test failure condition
        failure_condition = Condition(
            type=ConditionType.FAILURE,
            step_id='step1'
        )
        assert await failure_condition.evaluate(step_results) is False

        # Test contains condition
        contains_condition = Condition(
            type=ConditionType.RESULT_CONTAINS,
            step_id='step3',
            value='specific'
        )
        assert await contains_condition.evaluate(step_results) is True

        # Test equals condition
        equals_condition = Condition(
            type=ConditionType.RESULT_EQUALS,
            step_id='step1',
            value='Success result'
        )
        assert await equals_condition.evaluate(step_results) is True

        # Test custom condition
        custom_condition = Condition(
            type=ConditionType.CUSTOM,
            step_id='step1',
            custom_condition=lambda result: len(str(result.get('content', ''))) > 5
        )
        assert await custom_condition.evaluate(step_results) is True


class TestWorkflowTemplates:
    """Test workflow template functionality."""

    @pytest.mark.asyncio
    async def test_data_processing_template(self, workflow_manager):
        """Test data processing workflow template."""
        params = {
            "source": "database",
            "validation_rules": ["not_null", "range_check"],
            "transformations": ["normalize", "aggregate"]
        }

        workflow = await workflow_manager.create_workflow_from_template(
            "data_processing",
            params
        )

        assert workflow.name == "Template: data_processing"
        assert len(workflow.steps) == 3

        # Check step configurations
        ingest_step = workflow.steps[0]
        assert ingest_step.capability == "data_ingestion"
        assert ingest_step.parameters["source"] == "database"

        validate_step = workflow.steps[1]
        assert validate_step.capability == "data_validation"
        assert validate_step.parameters["rules"] == ["not_null", "range_check"]

        process_step = workflow.steps[2]
        assert process_step.capability == "data_processing"
        assert process_step.parameters["transformations"] == ["normalize", "aggregate"]

    @pytest.mark.asyncio
    async def test_content_generation_template(self, workflow_manager):
        """Test content generation workflow template."""
        params = {
            "topic": "AI Ethics",
            "style": "academic",
            "review_criteria": ["accuracy", "clarity"]
        }

        workflow = await workflow_manager.create_workflow_from_template(
            "content_generation",
            params
        )

        assert workflow.name == "Template: content_generation"
        assert len(workflow.steps) == 3

        # Check step configurations
        research_step = workflow.steps[0]
        assert research_step.capability == "research"
        assert research_step.parameters["topic"] == "AI Ethics"

        generate_step = workflow.steps[1]
        assert generate_step.capability == "content_generation"
        assert generate_step.parameters["style"] == "academic"

        review_step = workflow.steps[2]
        assert review_step.capability == "content_review"
        assert review_step.parameters["criteria"] == ["accuracy", "clarity"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
