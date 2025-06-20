from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from typing import Dict, Any, Set, Optional
import uuid
from datetime import datetime
from agents.core.message_types import AgentMessage

class DataProcessorAgent(BaseAgent):
    """
    Agent that processes data and updates the knowledge graph.
    Message content should include {'data': ...}
    """
    def __init__(self, agent_id: str = "data_processor_agent", capabilities: Optional[Set[Capability]] = None, config: Optional[Dict[str, Any]] = None):
        if capabilities is None:
            capabilities = {Capability(CapabilityType.MESSAGE_PROCESSING)}
        super().__init__(agent_id, "data_processor", capabilities, None, config)

    async def initialize(self) -> None:
        await super().initialize()
        self.logger.info("Data Processor Agent initialized")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        data = message.content.get('data')
        if not data:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"error": "No data provided."},
                timestamp=message.timestamp,
                message_type="data_processor_response"
            )
        try:
            await self.update_knowledge_graph({"data": data})
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "Data processed successfully."},
                timestamp=message.timestamp,
                message_type="data_processor_response"
            )
        except Exception as e:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"error": str(e)},
                timestamp=message.timestamp,
                message_type="data_processor_response"
            )

    async def query_knowledge_graph(self, query: dict) -> dict:
        return {}

    async def update_knowledge_graph(self, update_data: dict) -> None:
        """Update the knowledge graph with processed data."""
        try:
            self.logger.info(f"Updating knowledge graph with data: {update_data}")
            if self.knowledge_graph:
                await self.knowledge_graph.add_triple(
                    update_data.get('subject', ''),
                    update_data.get('predicate', ''),
                    update_data.get('object', '')
                )
        except Exception as e:
            self.logger.error(f"Error updating knowledge graph: {str(e)}")

 