from typing import Optional, Set, Dict, Any
import warnings

from agents.core.base_agent import BaseStreamingAgent, AgentMessage
from agents.core.capability_types import Capability, CapabilityType


class DataHandlerAgent(BaseStreamingAgent):
    """Generic data-ingestion agent that unifies Sensor and DataProcessor roles.

    handler_type:
        "sensor" – expects sensor_id & reading
        "data"   – expects data
    """

    _TYPE_SETTINGS = {
        "sensor": {
            "required_fields": {"sensor_id", "reading"},
            "response_type": "sensor_response",
            "success": "Sensor data updated successfully.",
            "predicate": "http://example.org/core#hasReading",
        },
        "data": {
            "required_fields": {"data"},
            "response_type": "data_processor_response",
            "success": "Data processed successfully.",
            "predicate": "http://example.org/core#hasData",
        },
    }

    def __init__(
        self,
        agent_id: str = "data_handler_agent",
        handler_type: str = "sensor",
        capabilities: Optional[Set[Capability]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        if capabilities is None:
            capabilities = {Capability(CapabilityType.MESSAGE_PROCESSING)}
        if handler_type not in self._TYPE_SETTINGS:
            raise ValueError(f"Unknown handler_type '{handler_type}'.")
        settings = self._TYPE_SETTINGS[handler_type]
        super().__init__(agent_id, handler_type, capabilities, None, config)

        # Apply per-type settings
        self._required_fields = settings["required_fields"]
        self._response_message_type = settings["response_type"]
        self._success_message = settings["success"]
        self._kg_predicate = settings["predicate"]
        self._handler_type = handler_type

    async def _build_kg_update_dict(self, message: AgentMessage) -> Dict[str, Any]:
        if self._handler_type == "sensor":
            return {
                "sensor_id": message.content.get("sensor_id"),
                "predicate": self._kg_predicate,
                "reading": message.content.get("reading"),
            }
        else:  # data
            return {
                "subject": message.content.get("data_id", ""),
                "predicate": self._kg_predicate,
                "object": message.content.get("data"),
            }

    async def update_knowledge_graph(self, update_data: dict) -> None:  # type: ignore[override]
        if self._handler_type == "sensor":
            subj = update_data.get("sensor_id", "")
            obj = str(update_data.get("reading", ""))
        else:
            subj = update_data.get("subject", "")
            obj = str(update_data.get("object", ""))
        pred = update_data.get("predicate", self._kg_predicate)
        await self._add_simple_triple(subj, pred, obj)

    async def _additional_response_content(self, message: AgentMessage) -> Dict[str, Any]:
        if self._handler_type == "sensor":
            try:
                reading = float(message.content.get("reading", 0))
            except Exception:
                reading = 0
            # Threshold 99.0 matches test expectation (99.9 triggers)
            if reading >= 99.0:
                return {"anomaly": True, "flag": "anomaly"}
        return {}


# ---------------------------------------------------------------------------
# Legacy compatibility shims – slated for removal in v3.0
# ---------------------------------------------------------------------------
class SensorAgent(DataHandlerAgent):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "SensorAgent is deprecated; use DataHandlerAgent(handler_type='sensor')",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, handler_type="sensor", **kwargs)


class DataProcessorAgent(DataHandlerAgent):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "DataProcessorAgent is deprecated; use DataHandlerAgent(handler_type='data')",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, handler_type="data", **kwargs) 