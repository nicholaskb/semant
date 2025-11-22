from agents.core.base_agent import BaseAgent, AgentMessage
from utils.ttl_validator import validate_ttl_file
import uuid
from datetime import datetime
from agents.core.message_types import AgentMessage

class TTLValidationAgent(BaseAgent):
    """
    Agent that validates Turtle (.ttl) files for RDF/OWL syntax errors.
    Message content should include {'file_path': ...}
    """
    def __init__(self, agent_id: str = "ttl_validation_agent"):
        super().__init__(agent_id, "ttl_validator")

    async def initialize(self) -> None:
        await super().initialize()
        self.logger.info("TTL Validation Agent initialized")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        file_path = message.content.get('file_path')
        if not file_path:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"error": "No file_path provided."},
                timestamp=message.timestamp,
                message_type="ttl_validation_response"
            )
        is_valid, result = validate_ttl_file(file_path)
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"is_valid": is_valid, "result": result},
            timestamp=message.timestamp,
            message_type="ttl_validation_response"
        )

    async def query_knowledge_graph(self, query: dict) -> dict:
        return {}

    async def update_knowledge_graph(self, update_data: dict) -> None:
        """TTLValidationAgent does not write to the shared KG."""
        pass 