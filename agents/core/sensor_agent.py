from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from typing import Dict, Any, Set, Optional
import uuid
from datetime import datetime
from agents.core.message_types import AgentMessage

class SensorAgent(BaseAgent):
    """
    Agent that processes sensor data and updates the knowledge graph.
    Message content should include {'sensor_id': ..., 'reading': ...}
    """
    def __init__(self, agent_id: str = "sensor_agent", capabilities: Optional[Set[Capability]] = None, config: Optional[Dict[str, Any]] = None):
        if capabilities is None:
            capabilities = {Capability(CapabilityType.MESSAGE_PROCESSING)}
        super().__init__(agent_id, "sensor", capabilities, None, config)

    async def initialize(self) -> None:
        await super().initialize()
        self.logger.info("Sensor Agent initialized")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        sensor_id = message.content.get('sensor_id')
        reading = message.content.get('reading')
        if not sensor_id or reading is None:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"error": "Missing sensor_id or reading."},
                timestamp=message.timestamp,
                message_type="sensor_response"
            )
        try:
            await self.update_knowledge_graph({"sensor_id": sensor_id, "reading": reading})
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "Sensor data updated successfully."},
                timestamp=message.timestamp,
                message_type="sensor_response"
            )
        except Exception as e:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"error": str(e)},
                timestamp=message.timestamp,
                message_type="sensor_response"
            )

    async def query_knowledge_graph(self, query: dict) -> dict:
        return {}

    async def update_knowledge_graph(self, update_data: dict) -> None:
        """Update the knowledge graph with sensor data."""
        try:
            self.logger.info(f"Updating knowledge graph with sensor data: {update_data}")
            if self.knowledge_graph:
                await self.knowledge_graph.add_triple(
                    update_data.get('sensor_id', ''),
                    update_data.get('predicate', ''),
                    update_data.get('reading', '')
                )
        except Exception as e:
            self.logger.error(f"Error updating knowledge graph: {str(e)}")

 