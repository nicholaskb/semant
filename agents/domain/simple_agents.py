from typing import Any, Dict
from agents.core.base_agent import BaseAgent, AgentMessage


class SimpleResponderAgent(BaseAgent):
    """Base class for simple agents that return a predefined response."""

    def __init__(self, agent_id: str, agent_type: str, default_response: str):
        super().__init__(agent_id, agent_type)
        self.default_response = default_response

    async def initialize(self) -> None:  # pragma: no cover - no setup needed
        pass

    async def process_message(self, message: AgentMessage) -> AgentMessage:
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


class FinanceAgent(SimpleResponderAgent):
    def __init__(self, agent_id: str = "finance_agent"):
        super().__init__(agent_id, "finance", "Finance information not available.")


class CoachingAgent(SimpleResponderAgent):
    def __init__(self, agent_id: str = "coaching_agent"):
        super().__init__(agent_id, "coaching", "Keep learning and growing!")


class IntelligenceAgent(SimpleResponderAgent):
    def __init__(self, agent_id: str = "intelligence_agent"):
        super().__init__(agent_id, "intelligence", "No intelligence reports.")


class DeveloperAgent(SimpleResponderAgent):
    def __init__(self, agent_id: str = "developer_agent"):
        super().__init__(agent_id, "developer", "Code generation not supported.")
