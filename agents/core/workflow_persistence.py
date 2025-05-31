from typing import Dict, List, Any, Optional
from loguru import logger
import json
import os
import time
from datetime import datetime
from .base_agent import AgentMessage

class WorkflowPersistence:
    """Handles workflow persistence, versioning, and recovery."""
    
    def __init__(self, storage_dir: str = "data/workflows"):
        self.storage_dir = storage_dir
        self.logger = logger.bind(component="WorkflowPersistence")
        os.makedirs(storage_dir, exist_ok=True)
        
    async def save_workflow(self, workflow: Dict[str, Any]) -> str:
        """Save a workflow to persistent storage."""
        workflow_id = workflow["id"]
        version = workflow.get("version", "1.0")
        timestamp = datetime.now().isoformat()
        
        # Create versioned filename
        filename = f"{workflow_id}_v{version}_{timestamp}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        # Add metadata
        workflow_data = {
            "workflow": workflow,
            "metadata": {
                "version": version,
                "saved_at": timestamp,
                "agent_count": len(workflow.get("agents", [])),
                "state": workflow.get("state", "unknown")
            }
        }
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(workflow_data, f, indent=2)
            
        self.logger.info(f"Saved workflow {workflow_id} version {version}")
        return filepath
        
    async def load_workflow(self, workflow_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Load a workflow from persistent storage."""
        # Find latest version if not specified
        if not version:
            files = [f for f in os.listdir(self.storage_dir) if f.startswith(workflow_id)]
            if not files:
                raise ValueError(f"No saved workflow found for {workflow_id}")
            latest_file = sorted(files)[-1]
            filepath = os.path.join(self.storage_dir, latest_file)
        else:
            # Find specific version
            files = [f for f in os.listdir(self.storage_dir) 
                    if f.startswith(f"{workflow_id}_v{version}")]
            if not files:
                raise ValueError(f"Version {version} not found for workflow {workflow_id}")
            filepath = os.path.join(self.storage_dir, files[0])
            
        # Load from file
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        self.logger.info(f"Loaded workflow {workflow_id} version {data['metadata']['version']}")
        return data["workflow"]
        
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all saved workflows with their versions."""
        workflows = []
        for filename in os.listdir(self.storage_dir):
            if not filename.endswith('.json'):
                continue
                
            filepath = os.path.join(self.storage_dir, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
                workflows.append({
                    "workflow_id": data["workflow"]["id"],
                    "version": data["metadata"]["version"],
                    "saved_at": data["metadata"]["saved_at"],
                    "state": data["metadata"]["state"],
                    "agent_count": data["metadata"]["agent_count"]
                })
                
        return sorted(workflows, key=lambda x: x["saved_at"], reverse=True)
        
    async def get_workflow_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get version history for a workflow."""
        files = [f for f in os.listdir(self.storage_dir) if f.startswith(workflow_id)]
        history = []
        
        for filename in sorted(files):
            filepath = os.path.join(self.storage_dir, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
                history.append({
                    "version": data["metadata"]["version"],
                    "saved_at": data["metadata"]["saved_at"],
                    "state": data["metadata"]["state"],
                    "agent_count": data["metadata"]["agent_count"]
                })
                
        return history
        
    async def recover_workflow(self, workflow_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Recover a workflow to a specific version."""
        workflow = await self.load_workflow(workflow_id, version)
        
        # Add recovery metadata
        workflow["recovered_at"] = datetime.now().isoformat()
        workflow["recovered_from"] = version or "latest"
        workflow["state"] = "recovered"
        
        # Save recovery point
        await self.save_workflow(workflow)
        
        self.logger.info(f"Recovered workflow {workflow_id} to version {version or 'latest'}")
        return workflow

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a workflow by its ID."""
        return await self.load_workflow(workflow_id) 