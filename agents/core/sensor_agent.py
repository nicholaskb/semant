from agents.core.base_agent import BaseAgent, AgentMessage
from typing import Dict, Any, List, Optional

class SensorAgent(BaseAgent):
    """
    Agent that processes sensor data and updates the knowledge graph.
    Message content should include {'sensor_id': ..., 'reading': ...}
    """
    def __init__(self, agent_id: str = "sensor_agent", capabilities: Optional[List[str]] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, "sensor", capabilities, config)

    async def initialize(self) -> None:
        self.logger.info("Sensor Agent initialized")

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        sensor_id = message.content.get('sensor_id')
        reading = message.content.get('reading')
        if not sensor_id or reading is None:
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"error": "Missing sensor_id or reading."},
                timestamp=message.timestamp,
                message_type="sensor_response"
            )
        try:
            await self.update_knowledge_graph({"sensor_id": sensor_id, "reading": reading})
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"status": "Sensor data updated successfully."},
                timestamp=message.timestamp,
                message_type="sensor_response"
            )
        except Exception as e:
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
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
            raise 