from typing import Dict, List, Any, Optional, Union
import asyncio
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
from agents.core.json_serialization import (
    custom_json_dump,
    custom_json_load,
    custom_json_dumps,
    custom_json_loads,
    make_json_serializable
)

class WorkflowPersistence:
    """Handles persistence of workflow state."""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """Initialize workflow persistence.

        Args:
            storage_dir: Optional path where workflow files should be stored. If not provided,
                a persistent directory named ``workflows`` under the current working
                directory (or path specified by the ``SEMANT_WORKSPACE`` environment
                variable) is used.  The directory is created if it does not exist.
        """
        # Determine storage location – allow caller override for tests while
        # defaulting to a persistent on-disk directory so workflow data survive
        # process restarts.
        if storage_dir is None:
            workspace_root = os.getenv("SEMANT_WORKSPACE", os.getcwd())
            storage_dir = os.path.join(workspace_root, "workflows")

        # Ensure the directory exists.
        os.makedirs(storage_dir, exist_ok=True)

        self.storage_dir = storage_dir
        self.logger = logger.bind(component="WorkflowPersistence", storage_dir=self.storage_dir)
        self._is_initialized = False
        self._initialization_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the persistence layer."""
        if self._is_initialized:
            return
        async with self._initialization_lock:
            if self._is_initialized:
                return
            # Ensure storage directory exists
            os.makedirs(self.storage_dir, exist_ok=True)
            self._is_initialized = True
            self.logger.debug("WorkflowPersistence initialized")

    async def shutdown(self) -> None:
        """Shutdown the persistence layer."""
        self.logger.info("WorkflowPersistence shut down")
        
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
                "metadata": make_json_serializable(workflow.metadata),
                "name": workflow.name,
                "description": workflow.description,
                "required_capabilities": make_json_serializable(workflow.required_capabilities)
            }
            
        # Ensure metadata block exists
        metadata = workflow_data.setdefault("metadata", {})
        metadata.setdefault("version", workflow_data.get("version", metadata.get("version", "1.0")))
        metadata["saved_at"] = datetime.now().isoformat()
        metadata["state"] = workflow_data.get("state", workflow_data.get("status", "created"))
        metadata["agent_count"] = len(workflow_data.get("agents", []))

        # Persist current version
        file_path = os.path.join(self.storage_dir, f"{workflow_data['id']}.json")
        # Convert to JSON-serializable format (handles sets, enums, etc.)
        serializable_data = make_json_serializable(workflow_data)
        with open(file_path, "w") as f:
            custom_json_dump(serializable_data, f, indent=2)

        # Append to history file
        history_path = os.path.join(self.storage_dir, f"{workflow_data['id']}_history.json")
        history: List[Dict] = []
        if os.path.exists(history_path):
            with open(history_path, "r") as f:
                try:
                    history = custom_json_load(f)
                except Exception:
                    history = []
        history.append(make_json_serializable(metadata.copy()))
        with open(history_path, "w") as f:
            custom_json_dump(history, f, indent=2)
            
    async def load_workflow(self, workflow_id: str) -> Optional[Union[Dict, Workflow]]:
        """Load workflow state."""
        file_path = os.path.join(self.storage_dir, f"{workflow_id}.json")
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, "r") as f:
            data = custom_json_load(f)
            
        # Return as dictionary if no steps field (old format)
        if 'steps' not in data:
            return data
            
        # Reconstruct required_capabilities as a set
        required_caps = data.get("required_capabilities", [])
        if isinstance(required_caps, list):
            required_caps = set(required_caps)
        elif not isinstance(required_caps, set):
            required_caps = set()
        
        wf_obj = Workflow(
            id=data["id"],
            steps=[self._dict_to_step(step) for step in data["steps"]],
            status=WorkflowStatus(data["status"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            error=data.get("error"),
            metadata=data.get("metadata", {}),
            name=data.get("name", ""),
            description=data.get("description", ""),
            required_capabilities=required_caps
        )

        # Return as dictionary for test compatibility
        return {
            "id": wf_obj.id,
            "state": wf_obj.status.value,
            "created_at": wf_obj.created_at,
            "updated_at": wf_obj.updated_at,
            "error": wf_obj.error,
            "metadata": wf_obj.metadata,
            "steps": data["steps"],
            "name": wf_obj.name,
            "description": wf_obj.description,
            "required_capabilities": list(wf_obj.required_capabilities)  # Convert set to list for JSON compatibility
        }
        
    async def get_workflow_history(self, workflow_id: str) -> List[Dict]:
        """Get version history for a workflow."""
        file_path = os.path.join(self.storage_dir, f"{workflow_id}_history.json")
        if not os.path.exists(file_path):
            return []
            
        with open(file_path, "r") as f:
            return custom_json_load(f)
            
    async def save_workflow_history(self, workflow_id: str, history: List[Dict]) -> None:
        """Save workflow version history."""
        file_path = os.path.join(self.storage_dir, f"{workflow_id}_history.json")
        with open(file_path, "w") as f:
            custom_json_dump(make_json_serializable(history), f, indent=2)
            
    def _step_to_dict(self, step: WorkflowStep) -> Dict:
        """Convert a workflow step to a dictionary."""
        # Handle capability serialization
        # WorkflowStep.capability is typed as str, but we need to handle
        # both string and Capability object cases for compatibility
        capability_value = step.capability
        if capability_value:
            if hasattr(capability_value, 'to_dict'):
                # It's a Capability object
                capability_value = capability_value.to_dict()
            elif not isinstance(capability_value, str):
                # Convert to string if it's not already
                capability_value = str(capability_value)
        
        return {
            "id": step.id,
            "capability": capability_value,
            "parameters": make_json_serializable(step.parameters),
            "status": step.status.value if hasattr(step.status, 'value') else str(step.status),
            "assigned_agent": step.assigned_agent,
            "error": step.error,
            "start_time": step.start_time,
            "end_time": step.end_time,
            "next_steps": make_json_serializable(step.next_steps) if hasattr(step, 'next_steps') else []
        }
        
    def _dict_to_step(self, data: Dict) -> WorkflowStep:
        """Convert a dictionary to a workflow step."""
        # Handle capability deserialization
        # WorkflowStep expects capability as a string, but we support
        # both dict (from Capability.to_dict()) and string formats
        capability_value = data.get("capability")
        if capability_value:
            if isinstance(capability_value, dict):
                # It's a Capability dict - convert to string representation
                # Import here to avoid circular imports
                from agents.core.capability_types import Capability
                cap_obj = Capability.from_dict(capability_value)
                capability_value = str(cap_obj.type.value) if hasattr(cap_obj, 'type') else str(cap_obj)
            elif not isinstance(capability_value, str):
                # Ensure it's a string
                capability_value = str(capability_value)
        
        # Handle status deserialization
        status_value = data.get("status")
        if isinstance(status_value, str):
            status = WorkflowStatus(status_value)
        elif hasattr(status_value, 'value'):
            status = WorkflowStatus(status_value.value)
        else:
            status = WorkflowStatus.PENDING
        
        return WorkflowStep(
            id=data.get("id", ""),
            capability=capability_value or "",
            parameters=data.get("parameters", {}),
            status=status,
            assigned_agent=data.get("assigned_agent"),
            error=data.get("error"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            next_steps=data.get("next_steps", [])
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
                data = custom_json_loads(content)
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