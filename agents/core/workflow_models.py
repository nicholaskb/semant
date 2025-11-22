"""Single source of truth for Workflow dataclasses and enum.

This module eliminates the duplicate Workflow/WorkflowStep/WorkflowStatus
implementations that previously existed across workflow_manager.py and
workflow_types.py.  All other modules should import the data-model via
`agents.core.workflow_types`, which re-exports these symbols for backward
compatibility.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class WorkflowStatus(str, Enum):
    """Lifecycle states of a workflow."""

    CREATED = "created"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ASSEMBLED = "assembled"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step inside a workflow execution graph."""

    id: str = ""
    capability: str = ""
    parameters: Dict = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    assigned_agent: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    next_steps: List[str] = field(default_factory=list)

    # --------- compatibility helper ---------
    @classmethod
    def build(cls, *, id: str, capability: str, parameters: Dict | None = None):
        """Factory allowing legacy call sites to create a step without relying on positional args."""
        return cls(id=id, capability=capability, parameters=parameters or {})


@dataclass(init=False)
class Workflow:
    """Declarative representation of a workflow.

    The canonical identifier is `id`; `workflow_id` is maintained as a
    read-only alias for backward compatibility with older test suites.
    """

    id: str
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None

    # Descriptive metadata
    name: str = ""
    description: str = ""
    required_capabilities: Set[str] = field(default_factory=set)
    metadata: Dict = field(default_factory=dict)

    # Internal alias storage (not included in dataclass repr by default)
    _workflow_id_alias: str = field(init=False, repr=False)

    def __init__(
        self,
        *,
        workflow_id: Optional[str] = None,
        id: Optional[str] = None,
        **kwargs,
    ):
        # Resolve primary identifier
        self.id = id or workflow_id or str(uuid.uuid4())
        self._workflow_id_alias = self.id

        # Map optional kwargs → attributes
        self.name = kwargs.get("name", "")
        self.description = kwargs.get("description", "")
        self.required_capabilities = set(kwargs.get("required_capabilities", []))
        self.metadata = kwargs.get("metadata", {})
        self.steps = kwargs.get("steps", [])
        self.status = kwargs.get("status", WorkflowStatus.PENDING)
        now = time.time()
        self.created_at = kwargs.get("created_at", now)
        self.updated_at = kwargs.get("updated_at", now)
        self.error = kwargs.get("error")

    # ---------------------
    # Back-compat property
    # ---------------------
    @property
    def workflow_id(self) -> str:  # noqa: D401 – simple alias property
        """Alias for tests or modules that still access `.workflow_id`."""
        return self._workflow_id_alias

    def __repr__(self):
        return f"<Workflow id={self.id} name={self.name} status={self.status}>"

    def __str__(self):
        return self.name or self.id

    def __eq__(self, other):
        if not isinstance(other, Workflow):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id) 