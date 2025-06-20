from typing import Dict, List, Any, Optional, Union
from loguru import logger
import json
import os
import time
from datetime import datetime
from agents.core.base_agent import AgentMessage
import aiofiles
import shutil
import tempfile
from agents.core.workflow_types import Workflow, WorkflowStatus, WorkflowStep

class WorkflowPersistence:
    """Handles persistence of workflow state."""
    
    def __init__(self):
        """Initialize workflow persistence."""
        self.storage_dir = tempfile.mkdtemp()
        self.logger = logger.bind(component="WorkflowPersistence")
        
    async def save_workflow(self, workflow: Union[Dict, Workflow]) -> None:
        """Save workflow state."""
        # Normalise to dictionary for storage
        if isinstance(workflow, dict):
            workflow_data = dict(workflow)  # Shallow copy
        else:
            status_value = "created" if workflow.status == WorkflowStatus.PENDING else workflow.status.value
            workflow_data = {
                "id": workflow.id,
                "steps": [self._step_to_dict(step) for step in workflow.steps],
                "status": status_value,
                "created_at": workflow.created_at,
                "updated_at": workflow.updated_at,
                "error": workflow.error,
                "metadata": workflow.metadata
            }
            
        # Ensure metadata block exists
        metadata = workflow_data.setdefault("metadata", {})
        metadata.setdefault("version", workflow_data.get("version", metadata.get("version", "1.0")))
        metadata["saved_at"] = datetime.now().isoformat()
        metadata["state"] = workflow_data.get("state", workflow_data.get("status", "created"))
        metadata["agent_count"] = len(workflow_data.get("agents", []))

        # Persist current version
        file_path = os.path.join(self.storage_dir, f"{workflow_data['id']}.json")
        with open(file_path, "w") as f:
            json.dump(workflow_data, f)

        # Append to history file
        history_path = os.path.join(self.storage_dir, f"{workflow_data['id']}_history.json")
        history: List[Dict] = []
        if os.path.exists(history_path):
            with open(history_path, "r") as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        history.append(metadata.copy())
        with open(history_path, "w") as f:
            json.dump(history, f)
            
    async def load_workflow(self, workflow_id: str) -> Optional[Union[Dict, Workflow]]:
        """Load workflow state."""
        file_path = os.path.join(self.storage_dir, f"{workflow_id}.json")
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, "r") as f:
            data = json.load(f)
            
        # Return as dictionary if no steps field (old format)
        if 'steps' not in data:
            return data
            
        wf_obj = Workflow(
            id=data["id"],
            steps=[self._dict_to_step(step) for step in data["steps"]],
            status=WorkflowStatus(data["status"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            error=data.get("error"),
            metadata=data.get("metadata")
        )

        # Return as dictionary for test compatibility
        return {
            "id": wf_obj.id,
            "state": wf_obj.status.value,
            "created_at": wf_obj.created_at,
            "updated_at": wf_obj.updated_at,
            "error": wf_obj.error,
            "metadata": wf_obj.metadata,
            "steps": data["steps"]
        }
        
    async def get_workflow_history(self, workflow_id: str) -> List[Dict]:
        """Get version history for a workflow."""
        file_path = os.path.join(self.storage_dir, f"{workflow_id}_history.json")
        if not os.path.exists(file_path):
            return []
            
        with open(file_path, "r") as f:
            return json.load(f)
            
    async def save_workflow_history(self, workflow_id: str, history: List[Dict]) -> None:
        """Save workflow version history."""
        file_path = os.path.join(self.storage_dir, f"{workflow_id}_history.json")
        with open(file_path, "w") as f:
            json.dump(history, f)
            
    def _step_to_dict(self, step: WorkflowStep) -> Dict:
        """Convert a workflow step to a dictionary."""
        # Handle capability serialization
        capability_dict = None
        if step.capability:
            if hasattr(step.capability, 'to_dict'):
                capability_dict = step.capability.to_dict()
            else:
                # Fallback for non-Capability objects
                capability_dict = str(step.capability)
        
        return {
            "id": step.id,
            "capability": capability_dict,
            "parameters": step.parameters,
            "status": step.status.value,
            "assigned_agent": step.assigned_agent,
            "error": step.error,
            "start_time": step.start_time,
            "end_time": step.end_time
        }
        
    def _dict_to_step(self, data: Dict) -> WorkflowStep:
        """Convert a dictionary to a workflow step."""
        # Handle capability deserialization
        capability = None
        if data.get("capability"):
            if isinstance(data["capability"], dict):
                # Import here to avoid circular imports
                from agents.core.capability_types import Capability
                capability = Capability.from_dict(data["capability"])
            else:
                # Fallback for string capabilities
                capability = data["capability"]
        
        return WorkflowStep(
            id=data["id"],
            capability=capability,
            parameters=data["parameters"],
            status=WorkflowStatus(data["status"]),
            assigned_agent=data.get("assigned_agent"),
            error=data.get("error"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time")
        )

    async def delete_workflow(self, workflow_id: str) -> None:
        """Delete workflow and its history."""
        # Delete current version
        file_path = os.path.join(self.storage_dir, f"{workflow_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Delete history
        history_path = os.path.join(self.storage_dir, f"{workflow_id}_history.json")
        if os.path.exists(history_path):
            os.remove(history_path)
            
        self.logger.info(f"Deleted workflow {workflow_id} and its history")

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all saved workflows with their versions."""
        workflows = []
        for filename in os.listdir(self.storage_dir):
            if not filename.endswith('.json'):
                continue
                
            filepath = os.path.join(self.storage_dir, filename)
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                data = json.loads(content)
                md = data.get("metadata", {})
                workflows.append({
                    "workflow_id": data.get("id"),
                    "version": md.get("version"),
                    "saved_at": md.get("saved_at"),
                    "state": md.get("state"),
                    "agent_count": md.get("agent_count", 0)
                })
                
        return sorted(workflows, key=lambda x: x["saved_at"], reverse=True)
        
    async def recover_workflow(self, workflow_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Recover a workflow to a specific version."""
        workflow = await self.load_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if isinstance(workflow, Workflow):
            # Convert to dict for easier patching
            workflow = {
                "id": workflow.id,
                "state": workflow.status.value,
                "metadata": workflow.metadata or {},
                "steps": [],
                "created_at": workflow.created_at,
                "updated_at": workflow.updated_at
            }

        # If specific version requested attempt to restore metadata fields from history
        if version:
            history = await self.get_workflow_history(workflow_id)
            for entry in history:
                if entry.get("version") == version:
                    # Rollback state to that entry's state
                    workflow["state"] = entry.get("state", workflow.get("state"))
                    workflow["version"] = entry.get("version", version)
                    break

        workflow.setdefault("metadata", {})
        workflow["metadata"]["recovered_at"] = datetime.now().isoformat()
        workflow["metadata"]["recovered_from"] = version or "latest"
        workflow["state"] = "recovered"

        # Save recovery point
        await self.save_workflow(workflow)
        
        self.logger.info(f"Recovered workflow {workflow_id} to version {version or 'latest'}")
        return workflow

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a workflow by its ID."""
        workflow = await self.load_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        return workflow 