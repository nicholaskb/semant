from typing import Dict, List, Set, Optional, Any
from loguru import logger
from .agent_registry import AgentRegistry, RegistryObserver
from .base_agent import AgentMessage, BaseAgent, AgentStatus
from .workflow_persistence import WorkflowPersistence
from .workflow_monitor import WorkflowMonitor
from .capability_types import Capability, CapabilityType, CapabilitySet
from .workflow_transaction import WorkflowTransaction
from .agent_health import AgentHealth, HealthCheck
import uuid
import time
import random
from collections import defaultdict
from datetime import datetime
import asyncio
import backoff
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from .workflow_types import Workflow, WorkflowStep, WorkflowStatus
from functools import lru_cache

class WorkflowStatus(str, Enum):
    """Status of a workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class WorkflowStep:
    """A step in a workflow."""
    id: str
    capability: str
    parameters: Dict
    status: WorkflowStatus = WorkflowStatus.PENDING
    assigned_agent: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

@dataclass
class Workflow:
    """A complete workflow."""
    id: str
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: float = time.time()
    updated_at: float = time.time()
    error: Optional[str] = None

class WorkflowManager(RegistryObserver):
    """Manages the execution of workflows across agents."""
    
    def __init__(self, agent_registry: AgentRegistry):
        self.agent_registry = agent_registry
        self.workflows: Dict[str, Workflow] = {}
        self._lock = asyncio.Lock()
        self.logger = logger.bind(component="WorkflowManager")
        self.agent_registry.add_observer(self)
        self._capability_cache: Dict[str, List[BaseAgent]] = {}
        self._cache_ttl = 60  # Cache TTL in seconds
        self._last_cache_update = time.time()
        
    async def create_workflow(self, steps: List[Dict]) -> Workflow:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())
        workflow_steps = [
            WorkflowStep(
                id=str(uuid.uuid4()),
                capability=step['capability'],
                parameters=step.get('parameters', {}),
            )
            for step in steps
        ]
        
        workflow = Workflow(
            id=workflow_id,
            steps=workflow_steps
        )
        
        async with self._lock:
            self.workflows[workflow_id] = workflow
            self.logger.info(f"Created workflow {workflow_id} with {len(steps)} steps")
            
        return workflow
        
    async def execute_workflow(self, workflow_id: str) -> None:
        """Execute a workflow with transaction support."""
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        transaction = WorkflowTransaction(workflow)
        async with transaction.transaction():
            workflow.status = WorkflowStatus.RUNNING
            workflow.updated_at = time.time()
            
            try:
                for step in workflow.steps:
                    await self._execute_step(workflow, step)
                    
                workflow.status = WorkflowStatus.COMPLETED
                workflow.updated_at = time.time()
                
            except Exception as e:
                self.logger.exception(f"Workflow {workflow_id} failed: {str(e)}")
                workflow.status = WorkflowStatus.FAILED
                workflow.error = str(e)
                workflow.updated_at = time.time()
                raise
            
    @lru_cache(maxsize=100)
    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID with caching."""
        async with self._lock:
            return self.workflows.get(workflow_id)
            
    async def _update_capability_cache(self) -> None:
        """Update the capability cache if TTL has expired."""
        current_time = time.time()
        if current_time - self._last_cache_update > self._cache_ttl:
            async with self._lock:
                self._capability_cache.clear()
                self._last_cache_update = current_time
                
    async def _get_cached_agents(self, capability: str) -> List[BaseAgent]:
        """Get agents for a capability from cache or registry."""
        await self._update_capability_cache()
        
        if capability not in self._capability_cache:
            agents = await self.agent_registry.get_agents_by_capability(capability)
            self._capability_cache[capability] = agents
            
        return self._capability_cache[capability]
        
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        max_time=30,
        giveup=lambda e: isinstance(e, ValueError)
    )
    async def _execute_step(self, workflow: Workflow, step: WorkflowStep) -> None:
        """Execute a single workflow step with retry logic and caching."""
        # Find available agent with required capability
        agents = await self._get_cached_agents(step.capability)
        if not agents:
            raise ValueError(f"No agent available with capability {step.capability}")
            
        # Select first available agent
        agent = agents[0]
        
        # Update step status
        async with self._lock:
            step.status = WorkflowStatus.RUNNING
            step.assigned_agent = agent.agent_id
            step.start_time = time.time()
            workflow.updated_at = time.time()
            
        try:
            # Execute task
            result = await agent.execute({
                'workflow_id': workflow.id,
                'step_id': step.id,
                'capability': step.capability,
                'parameters': step.parameters
            })
            
            # Update step status
            async with self._lock:
                step.status = WorkflowStatus.COMPLETED
                step.end_time = time.time()
                workflow.updated_at = time.time()
                
        except Exception as e:
            self.logger.exception(f"Step {step.id} failed: {str(e)}")
            async with self._lock:
                step.status = WorkflowStatus.FAILED
                step.error = str(e)
                step.end_time = time.time()
                workflow.updated_at = time.time()
            raise
            
    async def cancel_workflow(self, workflow_id: str) -> None:
        """Cancel a running workflow."""
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        async with self._lock:
            workflow.status = WorkflowStatus.CANCELLED
            workflow.updated_at = time.time()
            
    # RegistryObserver implementation
    async def on_agent_registered(self, agent: BaseAgent) -> None:
        """Handle agent registration."""
        self.logger.info(f"Agent {agent.agent_id} registered, checking pending workflows")
        await self._check_pending_workflows()
        
    async def on_agent_deregistered(self, agent_id: str) -> None:
        """Handle agent deregistration."""
        self.logger.info(f"Agent {agent_id} deregistered, updating affected workflows")
        await self._handle_agent_removal(agent_id)
        
    async def on_capability_updated(self, agent_id: str, capabilities: Set[str]) -> None:
        """Handle capability updates and invalidate cache."""
        self.logger.info(f"Agent {agent_id} capabilities updated, invalidating cache")
        self._capability_cache.clear()
        self._last_cache_update = time.time()
        await self._check_pending_workflows()
        
    async def _check_pending_workflows(self) -> None:
        """Check if any pending workflows can now be executed."""
        async with self._lock:
            for workflow in self.workflows.values():
                if workflow.status == WorkflowStatus.PENDING:
                    try:
                        await self.execute_workflow(workflow.id)
                    except Exception as e:
                        self.logger.error(f"Error executing workflow {workflow.id}: {e}")
                        
    async def _handle_agent_removal(self, agent_id: str) -> None:
        """Handle removal of an agent from running workflows."""
        async with self._lock:
            for workflow in self.workflows.values():
                if workflow.status == WorkflowStatus.RUNNING:
                    for step in workflow.steps:
                        if step.assigned_agent == agent_id and step.status == WorkflowStatus.RUNNING:
                            step.status = WorkflowStatus.FAILED
                            step.error = f"Assigned agent {agent_id} was removed"
                            step.end_time = time.time()
                            workflow.status = WorkflowStatus.FAILED
                            workflow.error = f"Workflow failed due to agent removal"
                            workflow.updated_at = time.time()

    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get the current status of a workflow."""
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            return {"status": "error", "message": f"Workflow {workflow_id} not found"}
        
        return {
            "state": workflow.status.value,
            "steps": [
                {
                    "id": step.id,
                    "capability": step.capability,
                    "status": step.status.value,
                    "assigned_agent": step.assigned_agent,
                    "error": step.error,
                    "start_time": step.start_time,
                    "end_time": step.end_time
                }
                for step in workflow.steps
            ]
        }
    
    async def get_workflow_metrics(
        self,
        workflow_id: str,
        metric_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get metrics for a workflow."""
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            return {}
            
        return await self.monitor.get_workflow_metrics(workflow_id, metric_type)

    async def get_active_alerts(
        self,
        workflow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get active alerts, optionally filtered by workflow."""
        return await self.monitor.get_active_alerts(workflow_id)
        
    async def validate_workflow(self, workflow_id: str) -> Dict:
        """Validate a workflow for cycles and other issues."""
        workflow = await self.persistence.load_workflow(workflow_id)
        if not workflow:
            return {
                "is_valid": False,
                "issues": [{
                    "type": "workflow_not_found",
                    "message": f"Workflow {workflow_id} not found"
                }]
            }

        issues = []
        # Check for cycles in agent dependencies
        visited = set()
        path = set()

        def has_cycle(agent_id):
            if agent_id in path:
                return True
            if agent_id in visited:
                return False

            visited.add(agent_id)
            path.add(agent_id)

            agent = self.registry.agents.get(agent_id)
            if agent and hasattr(agent, "dependencies"):
                for dep in agent.dependencies:
                    if has_cycle(dep):
                        return True

            path.remove(agent_id)
            return False

        for agent_id in workflow["agents"]:
            if has_cycle(agent_id):
                issues.append({
                    "type": "workflow_cycle",
                    "message": f"Cycle detected in workflow {workflow_id}",
                    "agent_id": agent_id
                })

        # Check for missing capabilities
        for capability in workflow["required_capabilities"]:
            capable_agents = await self.registry.get_agents_by_capability(capability)
            if not capable_agents:
                issues.append({
                    "type": "missing_capability",
                    "message": f"No agents available for capability: {capability}",
                    "capability": capability
                })

        return {
            "is_valid": len(issues) == 0,
            "issues": issues
        }
        
    async def get_workflow_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get version history for a workflow."""
        return await self.persistence.get_workflow_history(workflow_id)
        
    async def recover_workflow(self, workflow_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Recover a workflow to a specific version."""
        workflow = await self.persistence.recover_workflow(workflow_id, version)
        self._workflows[workflow_id] = workflow
        return workflow
        
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        return await self.monitor.get_system_health() 