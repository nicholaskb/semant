from typing import Any, Dict, List
from agents.core.base_agent import BaseAgent, AgentMessage


class DiaryAgent(BaseAgent):
    """Simple agent that stores diary entries in memory."""

    def __init__(self, agent_id: str = "diary_agent"):
        super().__init__(agent_id, "diary")
        self.entries: List[str] = []

    async def initialize(self) -> None:
        self.entries = []

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "add_entry":
            entry = message.content.get("entry", "")
            self.entries.append(entry)
            await self.update_knowledge_graph({"entry": entry})
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"status": "success"},
                timestamp=message.timestamp,
                message_type="add_entry_response",
            )
        elif message.message_type == "query_diary":
            query = message.content.get("query", "").lower()
            results = [e for e in self.entries if query in e.lower()]
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"results": results},
                timestamp=message.timestamp,
                message_type="query_diary_response",
            )
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"status": "error", "message": "Unknown message type"},
            timestamp=message.timestamp,
            message_type="error_response",
        )

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        if not self.knowledge_graph:
            return
        await self.knowledge_graph.update_graph(
            {f"entry:{len(self.entries)}": {"content": update_data.get("entry", "")}}
        )

    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        if not self.knowledge_graph:
            return {}
        sparql = query.get("sparql", "")
        return await self.knowledge_graph.query_graph(sparql)
