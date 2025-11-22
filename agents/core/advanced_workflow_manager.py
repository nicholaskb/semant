"""
Advanced Workflow Manager with Conditional Branching and Parallel Execution

Provides advanced workflow features including:
- Conditional branching based on task results
- Parallel task execution
- Dynamic workflow modification
- Workflow templates and reusable components

Date: 2025-01-11
Task: #14 - Implement Advanced Workflow Features
"""

import asyncio
import time
import uuid
from typing import Dict, List, Set, Optional, Any, Union, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from agents.core.workflow_manager import WorkflowManager
from agents.core.workflow_types import WorkflowStatus, Workflow, WorkflowStep
from agents.core.message_types import AgentMessage
from agents.core.base_agent import BaseAgent
from agents.core.capability_types import Capability, CapabilityType


class ExecutionMode(str, Enum):
    """Execution modes for workflow steps."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class ConditionType(str, Enum):
    """Types of conditions for branching."""
    SUCCESS = "success"
    FAILURE = "failure"
    RESULT_CONTAINS = "result_contains"
    RESULT_EQUALS = "result_equals"
    CUSTOM = "custom"


@dataclass
class Condition:
    """Represents a condition for workflow branching."""
    type: ConditionType
    step_id: str
    value: Optional[Any] = None
    custom_condition: Optional[Callable[[Any], bool]] = None

    async def evaluate(self, step_results: Dict[str, Any]) -> bool:
        """Evaluate the condition against step results."""
        if self.step_id not in step_results:
            return False

        result = step_results[self.step_id]

        if self.type == ConditionType.SUCCESS:
            return result.get('success', False)
        elif self.type == ConditionType.FAILURE:
            return not result.get('success', True)
        elif self.type == ConditionType.RESULT_CONTAINS:
            return self.value in str(result.get('content', ''))
        elif self.type == ConditionType.RESULT_EQUALS:
            return result.get('content') == self.value
        elif self.type == ConditionType.CUSTOM:
            return self.custom_condition(result) if self.custom_condition else False

        return False


@dataclass
class AdvancedWorkflowStep(WorkflowStep):
    """Extended workflow step with advanced features."""
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    conditions: List[Condition] = field(default_factory=list)
    parallel_group: Optional[str] = None  # Group ID for parallel execution
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {
        'max_retries': 3,
        'backoff_factor': 1.0,
        'retry_on': ['failure']
    })


@dataclass
class WorkflowBranch:
    """Represents a branch in a conditional workflow."""
    condition: Condition
    steps: List[str]  # Step IDs to execute if condition is met
    name: str = ""


@dataclass
class AdvancedWorkflow(Workflow):
    """Extended workflow with advanced features."""
    branches: List[WorkflowBranch] = field(default_factory=list)
    parallel_groups: Dict[str, List[str]] = field(default_factory=dict)  # group_id -> step_ids
    templates: Dict[str, List[str]] = field(default_factory=dict)  # template_name -> step_ids

    def __init__(self, *args, **kwargs):
        # Extract advanced workflow fields
        branches = kwargs.pop('branches', [])
        parallel_groups = kwargs.pop('parallel_groups', {})
        templates = kwargs.pop('templates', {})

        # Initialize parent Workflow
        super().__init__(*args, **kwargs)

        # Set advanced fields
        self.branches = branches
        self.parallel_groups = parallel_groups
        self.templates = templates


class AdvancedWorkflowManager(WorkflowManager):
    """
    Advanced workflow manager with conditional branching and parallel execution.

    Features:
    - Conditional branching based on task results
    - Parallel task execution within groups
    - Dynamic workflow modification during execution
    - Workflow templates for reusable patterns
    - Enhanced retry policies and error handling
    """

    def __init__(self, registry, knowledge_graph=None):
        super().__init__(registry, knowledge_graph)
        self._step_results: Dict[str, Dict[str, Any]] = {}
        self._parallel_tasks: Dict[str, Set[asyncio.Task]] = {}
        self.logger = logger.bind(component="AdvancedWorkflowManager")

    async def execute_advanced_workflow(self, workflow: AdvancedWorkflow) -> Dict[str, Any]:
        """
        Execute an advanced workflow with conditional branching and parallel execution.

        Args:
            workflow: The advanced workflow to execute

        Returns:
            Dictionary containing execution results and metadata
        """
        workflow_id = workflow.id
        self._workflows[workflow_id] = workflow
        self._step_results[workflow_id] = {}

        try:
            # Initialize workflow
            workflow.status = WorkflowStatus.RUNNING
            workflow.updated_at = time.time()

            # Execute workflow steps
            await self._execute_workflow_steps(workflow)

            # Check final status
            if all(step.status == WorkflowStatus.COMPLETED for step in workflow.steps):
                workflow.status = WorkflowStatus.COMPLETED
            else:
                workflow.status = WorkflowStatus.FAILED

        except Exception as e:
            self.logger.error(f"Workflow {workflow_id} failed: {e}")
            workflow.status = WorkflowStatus.FAILED
            workflow.error = str(e)

        finally:
            workflow.updated_at = time.time()
            await self._cleanup_parallel_tasks(workflow_id)

        return {
            'workflow_id': workflow_id,
            'status': workflow.status,
            'steps_executed': len(workflow.steps),
            'step_results': self._step_results.get(workflow_id, {}),
            'execution_time': workflow.updated_at - workflow.created_at,
            'error': workflow.error
        }

    async def _execute_workflow_steps(self, workflow: AdvancedWorkflow) -> None:
        """Execute workflow steps with advanced features."""
        # Group steps by execution mode
        sequential_steps = []
        parallel_groups = {}
        conditional_steps = []

        for step in workflow.steps:
            if isinstance(step, AdvancedWorkflowStep):
                if step.execution_mode == ExecutionMode.PARALLEL and step.parallel_group:
                    if step.parallel_group not in parallel_groups:
                        parallel_groups[step.parallel_group] = []
                    parallel_groups[step.parallel_group].append(step)
                elif step.execution_mode == ExecutionMode.CONDITIONAL:
                    conditional_steps.append(step)
                else:
                    sequential_steps.append(step)
            else:
                sequential_steps.append(step)

        # Execute sequential steps first
        for step in sequential_steps:
            await self._execute_step(workflow, step)

        # Execute parallel groups
        for group_id, steps in parallel_groups.items():
            await self._execute_parallel_group(workflow, group_id, steps)

        # Execute conditional steps
        for step in conditional_steps:
            if await self._should_execute_conditional_step(workflow, step):
                await self._execute_step(workflow, step)

    async def _execute_parallel_group(self, workflow: AdvancedWorkflow, group_id: str, steps: List[WorkflowStep]) -> None:
        """Execute a group of steps in parallel."""
        workflow_id = workflow.id
        self._parallel_tasks[workflow_id] = set()

        # Create tasks for parallel execution
        tasks = []
        for step in steps:
            task = asyncio.create_task(self._execute_step(workflow, step))
            tasks.append(task)
            self._parallel_tasks[workflow_id].add(task)

        # Wait for all parallel tasks to complete
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(f"Parallel execution failed for group {group_id}: {e}")
        finally:
            # Clean up completed tasks
            self._parallel_tasks[workflow_id].clear()

    async def _should_execute_conditional_step(self, workflow: AdvancedWorkflow, step: AdvancedWorkflowStep) -> bool:
        """Determine if a conditional step should be executed."""
        workflow_id = workflow.id
        step_results = self._step_results.get(workflow_id, {})

        # Check all conditions for this step
        for condition in step.conditions:
            if not await condition.evaluate(step_results):
                return False

        return True

    async def _execute_step(self, workflow: AdvancedWorkflow, step: WorkflowStep) -> None:
        """Execute a single workflow step with enhanced error handling."""
        workflow_id = workflow.id
        step.status = WorkflowStatus.RUNNING
        step.start_time = time.time()

        try:
            # Find suitable agent
            agent = await self._find_agent_for_capability(step.capability)
            if not agent:
                raise ValueError(f"No agent found for capability: {step.capability}")

            # Create message
            message = AgentMessage(
                sender_id=f"workflow_{workflow_id}",
                recipient_id=agent.agent_id,
                content=step.parameters,
                message_type="workflow_step",
                timestamp=time.time()
            )

            # Execute step with retry logic
            result = await self._execute_step_with_retry(workflow, step, agent, message)

            # Store result
            self._step_results[workflow_id][step.id] = result

            # Update step status
            if result.get('success', False):
                step.status = WorkflowStatus.COMPLETED
            else:
                step.status = WorkflowStatus.FAILED
                step.error = result.get('error', 'Unknown error')

        except Exception as e:
            self.logger.error(f"Step {step.id} failed: {e}")
            step.status = WorkflowStatus.FAILED
            step.error = str(e)

        finally:
            step.end_time = time.time()

    async def _execute_step_with_retry(self, workflow: AdvancedWorkflow, step: AdvancedWorkflowStep,
                                      agent: BaseAgent, message: AgentMessage) -> Dict[str, Any]:
        """Execute a step with retry logic."""
        retry_policy = step.retry_policy if isinstance(step, AdvancedWorkflowStep) else {'max_retries': 3}

        max_retries = retry_policy.get('max_retries', 3)
        backoff_factor = retry_policy.get('backoff_factor', 1.0)
        retry_on = retry_policy.get('retry_on', ['failure'])

        for attempt in range(max_retries + 1):
            try:
                response = await agent.process_message(message)

                result = {
                    'success': response.content.get('success', True),
                    'content': response.content,
                    'attempt': attempt + 1
                }

                # Check if we should retry
                if not result['success'] and 'failure' in retry_on:
                    if attempt < max_retries:
                        delay = backoff_factor * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue

                return result

            except Exception as e:
                if attempt < max_retries and 'exception' in retry_on:
                    delay = backoff_factor * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    return {
                        'success': False,
                        'error': str(e),
                        'attempt': attempt + 1
                    }

        return {'success': False, 'error': 'Max retries exceeded'}

    async def _find_agent_for_capability(self, capability: str) -> Optional[BaseAgent]:
        """Find an available agent for the given capability."""
        # Refresh cache if expired or empty
        if (time.time() - self._last_cache_update > self._cache_ttl) or not self._capability_cache:
            await self._refresh_capability_cache()

        agents = self._capability_cache.get(capability, [])
        if not agents:
            return None

        # Return first available agent
        for agent in agents:
            if agent.status == 'idle':
                return agent

        return agents[0] if agents else None

    async def _refresh_capability_cache(self) -> None:
        """Refresh the capability cache."""
        self._capability_cache.clear()

        agents = self.registry.get_all_agents()
        for agent in agents:
            try:
                capabilities = await agent.get_capabilities()
                for cap in capabilities:
                    # Normalize capability to string for cache key
                    # Handle both Capability objects and strings
                    if isinstance(cap, Capability):
                        cap_key = cap.type.value
                    elif isinstance(cap, CapabilityType):
                        cap_key = cap.value
                    else:
                        cap_key = str(cap)
                    
                    if cap_key not in self._capability_cache:
                        self._capability_cache[cap_key] = []
                    self._capability_cache[cap_key].append(agent)
            except Exception as e:
                self.logger.warning(f"Failed to get capabilities for agent {agent.agent_id}: {e}")

        self._last_cache_update = time.time()

    async def _cleanup_parallel_tasks(self, workflow_id: str) -> None:
        """Clean up any remaining parallel tasks for a workflow."""
        if workflow_id in self._parallel_tasks:
            tasks = self._parallel_tasks[workflow_id]
            for task in tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            del self._parallel_tasks[workflow_id]

    # Workflow Template Methods

    async def create_workflow_from_template(self, template_name: str, parameters: Dict[str, Any]) -> AdvancedWorkflow:
        """
        Create a workflow from a predefined template.

        Args:
            template_name: Name of the template to use
            parameters: Parameters to customize the template

        Returns:
            Configured advanced workflow
        """
        # This would load templates from a registry/database
        # For now, return a basic workflow
        workflow = AdvancedWorkflow(
            id=f"template-{template_name}-{uuid.uuid4().hex[:8]}",
            name=f"Template: {template_name}",
            description=f"Workflow created from template {template_name}"
        )

        # Add template-specific steps based on template_name
        if template_name == "data_processing":
            workflow.steps = [
                AdvancedWorkflowStep(
                    id="ingest",
                    capability="data_ingestion",
                    parameters={"source": parameters.get("source")}
                ),
                AdvancedWorkflowStep(
                    id="validate",
                    capability="data_validation",
                    parameters={"rules": parameters.get("validation_rules")}
                ),
                AdvancedWorkflowStep(
                    id="process",
                    capability="data_processing",
                    parameters={"transformations": parameters.get("transformations")}
                )
            ]
        elif template_name == "content_generation":
            workflow.steps = [
                AdvancedWorkflowStep(
                    id="research",
                    capability="research",
                    parameters={"topic": parameters.get("topic")}
                ),
                AdvancedWorkflowStep(
                    id="generate",
                    capability="content_generation",
                    parameters={"style": parameters.get("style")}
                ),
                AdvancedWorkflowStep(
                    id="review",
                    capability="content_review",
                    parameters={"criteria": parameters.get("review_criteria")}
                )
            ]

        return workflow

    async def modify_workflow_dynamically(self, workflow_id: str, modifications: Dict[str, Any]) -> bool:
        """
        Modify a running workflow dynamically.

        Args:
            workflow_id: ID of the workflow to modify
            modifications: Changes to apply

        Returns:
            True if modification was successful
        """
        if workflow_id not in self._workflows:
            return False

        workflow = self._workflows[workflow_id]

        # Apply modifications
        if 'add_steps' in modifications:
            for step_data in modifications['add_steps']:
                new_step = AdvancedWorkflowStep(**step_data)
                workflow.steps.append(new_step)

        if 'remove_steps' in modifications:
            step_ids_to_remove = set(modifications['remove_steps'])
            workflow.steps = [s for s in workflow.steps if s.id not in step_ids_to_remove]

        if 'update_steps' in modifications:
            for step_update in modifications['update_steps']:
                step_id = step_update['id']
                for step in workflow.steps:
                    if step.id == step_id:
                        for key, value in step_update.items():
                            if key != 'id':
                                setattr(step, key, value)
                        break

        workflow.updated_at = time.time()
        return True

    # Monitoring and Analytics

    def get_workflow_analytics(self) -> Dict[str, Any]:
        """Get analytics about workflow execution."""
        return {
            'total_workflows': len(self._workflows),
            'active_workflows': len([w for w in self._workflows.values() if w.status == WorkflowStatus.RUNNING]),
            'completed_workflows': len([w for w in self._workflows.values() if w.status == WorkflowStatus.COMPLETED]),
            'failed_workflows': len([w for w in self._workflows.values() if w.status == WorkflowStatus.FAILED]),
            'average_execution_time': self._calculate_average_execution_time(),
            'parallel_execution_efficiency': self._calculate_parallel_efficiency()
        }

    def _calculate_average_execution_time(self) -> float:
        """Calculate average workflow execution time."""
        completed_workflows = [w for w in self._workflows.values() if w.status == WorkflowStatus.COMPLETED]
        if not completed_workflows:
            return 0.0

        total_time = sum(w.updated_at - w.created_at for w in completed_workflows)
        return total_time / len(completed_workflows)

    def _calculate_parallel_efficiency(self) -> float:
        """Calculate parallel execution efficiency."""
        # This would analyze parallel task execution patterns
        # For now, return a placeholder
        return 0.85  # 85% efficiency
