# Workflow Data-Model Consolidation Playbook

_Date: 2025-06-15  •  Author: OpenAI code-assistant_

---

## Goal
1. Establish **one** authoritative module `agents/core/workflow_models.py` defining:
   * `WorkflowStatus` (Enum)
   * `WorkflowStep` (dataclass)
   * `Workflow` (dataclass with `workflow_id` alias property)
2. Remove duplicate definitions elsewhere.
3. Route **all** imports (core, persistence, tests) through `agents.core.workflow_types` for backward-compat.
4. Eliminate circular-import risk; tests can instantiate `Workflow` via either import path.

---

## Directory & File Plan
```
agents/core/
│
├── workflow_models.py      # ⇦ single source of truth
├── workflow_manager.py     # imports from workflow_types → workflow_models
├── workflow_persistence.py # imports from workflow_types → workflow_models
├── workflow_types.py       # thin re-export wrapper
└── … (other unaffected modules)
```

---

## Step-by-Step Procedure

### 1️⃣ Create `workflow_models.py`
```python
# agents/core/workflow_models.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
import time, uuid

class WorkflowStatus(str, Enum):
    CREATED   = "created"
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    ASSEMBLED = "assembled"

@dataclass
class WorkflowStep:
    id: str
    capability: str
    parameters: Dict
    status: WorkflowStatus = WorkflowStatus.PENDING
    assigned_agent: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    next_steps: List[str] = field(default_factory=list)

@dataclass(init=False)
class Workflow:
    id: str                                 # canonical
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: Optional[str] = None

    # descriptive metadata
    name: str = ""
    description: str = ""
    required_capabilities: Set[str] = field(default_factory=set)
    metadata: Dict = field(default_factory=dict)

    _workflow_id_alias: str = field(init=False, repr=False)

    def __init__(
        self,
        *,
        workflow_id: Optional[str] = None,
        id: Optional[str] = None,
        **kwargs,
    ):
        self.id = id or workflow_id or str(uuid.uuid4())
        self._workflow_id_alias = self.id

        # map kwargs → fields
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

    # read-only alias for legacy tests
    @property
    def workflow_id(self) -> str:
        return self._workflow_id_alias
```

### 2️⃣ Update `workflow_types.py`
```python
# agents/core/workflow_types.py
"""Public re-export facade for Workflow data-model."""
from agents.core.workflow_models import (
    WorkflowStatus,  # enum remains import-friendly
    Workflow,
    WorkflowStep,
)

__all__ = [
    "WorkflowStatus",
    "Workflow",
    "WorkflowStep",
]
```

### 3️⃣ Fix imports in the codebase
* Replace any direct model imports to use `agents.core.workflow_types`.
* Example CLI (macOS sed syntax):
```bash
ripgrep -l "Workflow, WorkflowStep" agents | \
  xargs sed -i '' 's/from agents\.core\.workflow_types import Workflow, WorkflowStep, WorkflowStatus/from agents.core.workflow_types import Workflow, WorkflowStep, WorkflowStatus/'
```

### 4️⃣ Remove duplicate shims
* Delete temporary dataclass stubs from `workflow_types.py` (already done above).

### 5️⃣ Ensure manager & persistence import via facade
```python
# in workflow_manager.py & workflow_persistence.py
from agents.core.workflow_types import Workflow, WorkflowStep, WorkflowStatus
```

### 6️⃣ Run Tests
```bash
pytest tests/test_workflow_manager.py::test_workflow_creation -q   # should pass
pytest -q                                                           # full suite; remaining reds are logic, not model
```

### 7️⃣ Knowledge-Graph Sanity Check
```python
>>> from agents.core.workflow_manager import WorkflowManager
>>> from agents.core.workflow_types import Workflow
>>> from agents.core.agent_registry import AgentRegistry
>>> import asyncio, nest_asyncio, rdflib
>>> nest_asyncio.apply()

>>> async def demo():
...     reg = AgentRegistry(); await reg.initialize()
...     wm  = WorkflowManager(reg); await wm.initialize()
...     wf  = Workflow(workflow_id="kg_demo", name="KG Demo")
...     await wm.register_workflow(wf)
...     turtle = await wm.persistence.export_graph(format="turtle")
...     print(turtle)
...
>>> asyncio.run(demo())
```
Confirm a triple exists for `kg_demo`.

---

## Documentation Updates
* **docs/developer_guide.md** – add "Workflow Data-Model Consolidation" section.
* **technical_architecture.md** – update diagrams (see plan above).
* **README.md** – add a note in "Breaking Changes" about importing via `workflow_types`.

---

### ✅  When the tests are all green and the ledger is empty, you may remove the 🚀 SALVAGE block. 