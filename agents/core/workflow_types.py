from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

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
    created_at: float = 0.0
    updated_at: float = 0.0
    error: Optional[str] = None 