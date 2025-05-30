from typing import Any, Dict
from datetime import datetime

from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger


class JudgeAgent(BaseAgent):
    """Agent that evaluates whether actions were properly logged."""

    def __init__(self, agent_id: str = "judge_agent", kg: KnowledgeGraphManager | None = None):
        super().__init__(agent_id, "judge")
        self.logger = logger.bind(agent_id=agent_id)
        self.knowledge_graph = kg

    async def initialize(self) -> None:  # pragma: no cover - simple init
        self.logger.info("Judge Agent initialized")

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "evaluate_challenge":
            decision = await self.evaluate_challenge(message.content.get("challenge", ""))
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"decision": decision},
                timestamp=message.timestamp,
                message_type="judge_response",
            )
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"status": "error", "message": "Unknown message type"},
            timestamp=message.timestamp,
            message_type="error_response",
        )

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:  # pragma: no cover - not used
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph(update_data)

    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - not used
        if not self.knowledge_graph:
            return {}
        return await self.knowledge_graph.query_graph(query.get("sparql", ""))

    async def evaluate_challenge(self, challenge_data: str) -> str:
        """Check if any email entries exist in the knowledge graph."""
        if not self.knowledge_graph:
            decision = "NoGraph"
        else:
            results = await self.knowledge_graph.query_graph(
                "SELECT ?s WHERE {?s ?p ?o . FILTER STRSTARTS(STR(?s), 'email:')}"
            )
            decision = "Approved" if results else "Rejected"

        diary_entry = (
            f"{self.agent_id} evaluated challenge as {decision} at {datetime.utcnow().isoformat()}"
        )
        self.write_diary(diary_entry)
        return decision
