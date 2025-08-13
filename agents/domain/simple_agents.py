from typing import Any, Dict
from agents.core.base_agent import BaseAgent, AgentMessage
import uuid
from datetime import datetime
from agents.core.message_types import AgentMessage


class SimpleResponderAgent(BaseAgent):
    """Base class for simple agents that return a predefined response."""

    def __init__(self, agent_id: str, agent_type: str, default_response: str):
        super().__init__(agent_id, agent_type)
        self.default_response = default_response

    async def initialize(self) -> None:  # pragma: no cover - no setup needed
        pass

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"response": self.default_response},
            timestamp=message.timestamp,
            message_type="response",
        )

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:  # pragma: no cover - simple agent
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph(update_data)

    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - simple agent
        if not self.knowledge_graph:
            return {}
        return await self.knowledge_graph.query_graph(query.get("sparql", ""))


    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages - REQUIRED IMPLEMENTATION."""
        try:
            # Process the message based on its type and content
            response_content = f"Agent {self.agent_id} processed: {message.content}"
            
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=response_content,
                message_type=getattr(message, 'message_type', 'response'),
                timestamp=datetime.now()
            )
        except Exception as e:
            # Error handling
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=f"Error processing message: {str(e)}",
                message_type="error",
                timestamp=datetime.now()
            )


class FinanceAgent(SimpleResponderAgent):
    def __init__(self, agent_id: str = "finance_agent", **kwargs):
        super().__init__(agent_id, "finance", "Finance information not available.")


class CoachingAgent(SimpleResponderAgent):
    def __init__(self, agent_id: str = "coaching_agent", **kwargs):
        super().__init__(agent_id, "coaching", "Keep learning and growing!")


class IntelligenceAgent(SimpleResponderAgent):
    def __init__(self, agent_id: str = "intelligence_agent", **kwargs):
        super().__init__(agent_id, "intelligence", "No intelligence reports.")


class DeveloperAgent(SimpleResponderAgent):
    def __init__(self, agent_id: str = "developer_agent", **kwargs):
        super().__init__(agent_id, "developer", "Code generation not supported.")
