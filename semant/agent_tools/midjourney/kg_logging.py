"""
Knowledge Graph logging utilities for Midjourney agent tools.

Responsibilities:
- Initialize and use the shared KnowledgeGraphManager
- Record each tool invocation as a ToolCall entity
- Link to a Task entity when GoAPI returns a task id
- Persist inputs/outputs (as JSON literals) and represent images as schema:ImageObject

RDF Conventions (URIs):
- mj namespace:   http://example.org/midjourney#
- schema.org:     http://schema.org/
- core namespace: http://example.org/core#

Notes:
- We avoid binding namespaces directly; KnowledgeGraphManager can store fully
  qualified URIs as strings. It will convert http(s) objects to URIRefs.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from kg.models.graph_manager import KnowledgeGraphManager


logger = logging.getLogger(__name__)

# Process-wide shared KG instance to unify logging and queries across components
_GLOBAL_KG: KnowledgeGraphManager | None = None

def set_global_kg(manager: KnowledgeGraphManager) -> None:
    global _GLOBAL_KG
    _GLOBAL_KG = manager

def get_global_kg() -> KnowledgeGraphManager:
    global _GLOBAL_KG
    if _GLOBAL_KG is None:
        _GLOBAL_KG = KnowledgeGraphManager()
    return _GLOBAL_KG


MJ_NS = "http://example.org/midjourney#"
CORE_NS = "http://example.org/core#"
SCHEMA_NS = "http://schema.org/"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_json_literal(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return json.dumps({"value": str(value)})


class KGLogger:
    """Lightweight logger for recording Midjourney tool calls to the KG."""

    def __init__(self, kg: Optional[KnowledgeGraphManager] = None, *, agent_id: str = "agent/UnknownAgent") -> None:
        # Prefer provided manager; otherwise use process-wide shared manager
        self.kg = kg or get_global_kg()
        # Expect caller to pass e.g. "agent/Planner" → we expand to full URI below
        self.agent_uri = f"http://example.org/{agent_id}" if not agent_id.startswith("http") else agent_id
        self.metrics: Dict[str, int] = {
            "tool_calls": 0,
            "images_logged": 0,
        }
        self._init_lock = asyncio.Lock()

    async def _ensure_initialized(self) -> None:
        if not await self.kg.is_initialized():
            async with self._init_lock:
                if not await self.kg.is_initialized():
                    await self.kg.initialize()

    async def log_tool_call(
        self,
        *,
        tool_name: str,
        inputs: Dict[str, Any],
        outputs: Optional[Dict[str, Any]] = None,
        goapi_task: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Record a tool call and return created URIs.

        - tool_name: logical tool label (e.g., "mj.imagine")
        - inputs: structured input parameters
        - outputs: raw response payload
        - goapi_task: raw task object; task id will be extracted if present
        - images: list of image URLs to materialize as schema:ImageObject
        """
        await self._ensure_initialized()

        # Create a unique ToolCall node
        call_id = str(uuid.uuid4())
        call_uri = f"{MJ_NS}ToolCall/{call_id}"

        await self.kg.add_triple(call_uri, f"{CORE_NS}name", tool_name)
        await self.kg.add_triple(call_uri, f"{CORE_NS}type", f"{MJ_NS}ToolCall")
        await self.kg.add_triple(call_uri, f"{CORE_NS}timestamp", _iso_now())
        await self.kg.add_triple(call_uri, f"{CORE_NS}performedBy", self.agent_uri)

        # Persist inputs/outputs as JSON literals
        await self.kg.add_triple(call_uri, f"{MJ_NS}input", _as_json_literal(inputs))
        if outputs is not None:
            await self.kg.add_triple(call_uri, f"{MJ_NS}output", _as_json_literal(outputs))

        # Link to an mj:Task if we can extract a task id
        task_uri = None
        task_id = _extract_task_id(goapi_task or outputs)
        if task_id:
            task_uri = f"{MJ_NS}Task/{task_id}"
            await self.kg.add_triple(task_uri, f"{CORE_NS}type", f"{MJ_NS}Task")
            await self.kg.add_triple(task_uri, f"{CORE_NS}status", "created")
            await self.kg.add_triple(call_uri, f"{CORE_NS}relatedTo", task_uri)

        # Represent images as schema:ImageObject and link to the call
        if images:
            for url in images:
                image_uri = f"{SCHEMA_NS}ImageObject/{uuid.uuid5(uuid.NAMESPACE_URL, url)}"
                await self.kg.add_triple(image_uri, f"{CORE_NS}type", f"{SCHEMA_NS}ImageObject")
                await self.kg.add_triple(image_uri, f"{SCHEMA_NS}contentUrl", url)
                await self.kg.add_triple(call_uri, f"{SCHEMA_NS}associatedMedia", image_uri)
                self.metrics["images_logged"] += 1

        self.metrics["tool_calls"] += 1
        return {"call_uri": call_uri, "task_uri": task_uri or ""}


def _extract_task_id(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if not payload or not isinstance(payload, dict):
        return None
    # Common shapes: {"data": {"task_id": "..."}}, {"task_id": "..."}, {"id": "..."}
    try:
        if "data" in payload and isinstance(payload["data"], dict):
            inner = payload["data"]
            if "task_id" in inner:
                return str(inner["task_id"]) or None
            if "id" in inner:
                return str(inner["id"]) or None
        if "task_id" in payload:
            return str(payload["task_id"]) or None
        if "id" in payload:
            return str(payload["id"]) or None
    except Exception:
        return None
    return None


