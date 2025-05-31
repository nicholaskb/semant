from typing import Dict, List, Optional, Any
from loguru import logger
import asyncio
from contextlib import asynccontextmanager
from .workflow_types import Workflow, WorkflowStep, WorkflowStatus

class WorkflowTransaction:
    """Handles workflow state transactions with rollback support."""
    
    def __init__(self, workflow: Workflow):
        self.workflow = workflow
        self._original_state = self._capture_state()
        self._lock = asyncio.Lock()
        self.logger = logger.bind(component="WorkflowTransaction")
        
    def _capture_state(self) -> Dict[str, Any]:
        """Capture the current state of the workflow."""
        return {
            "status": self.workflow.status,
            "steps": [
                {
                    "id": step.id,
                    "status": step.status,
                    "assigned_agent": step.assigned_agent,
                    "error": step.error,
                    "start_time": step.start_time,
                    "end_time": step.end_time
                }
                for step in self.workflow.steps
            ],
            "error": self.workflow.error,
            "updated_at": self.workflow.updated_at
        }
        
    async def commit(self) -> None:
        """Commit the transaction."""
        async with self._lock:
            self._original_state = self._capture_state()
            self.logger.info(f"Committed transaction for workflow {self.workflow.id}")
            
    async def rollback(self) -> None:
        """Rollback the workflow to its original state."""
        async with self._lock:
            # Restore workflow status
            self.workflow.status = self._original_state["status"]
            self.workflow.error = self._original_state["error"]
            self.workflow.updated_at = self._original_state["updated_at"]
            
            # Restore step states
            for step, original_step in zip(self.workflow.steps, self._original_state["steps"]):
                step.status = original_step["status"]
                step.assigned_agent = original_step["assigned_agent"]
                step.error = original_step["error"]
                step.start_time = original_step["start_time"]
                step.end_time = original_step["end_time"]
                
            self.logger.info(f"Rolled back workflow {self.workflow.id} to previous state")
            
    @asynccontextmanager
    async def transaction(self):
        """Context manager for workflow transactions."""
        try:
            yield self
            await self.commit()
        except Exception as e:
            self.logger.error(f"Transaction failed for workflow {self.workflow.id}: {e}")
            await self.rollback()
            raise 