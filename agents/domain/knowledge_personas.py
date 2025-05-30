from typing import Any, Dict
from agents.core.base_agent import BaseAgent, AgentMessage
from .simple_agents import SimpleResponderAgent


class KnowledgeGraphConsultant(SimpleResponderAgent):
    """Persona offering general knowledge graph consulting advice."""

    def __init__(self, agent_id: str = "kg_consultant"):
        super().__init__(agent_id, "knowledge_consultant", "I can help design and query your knowledge graph.")


class OpenAIKnowledgeGraphEngineer(SimpleResponderAgent):
    """Persona focused on engineering best practices for knowledge graphs."""

    def __init__(self, agent_id: str = "kg_engineer"):
        super().__init__(agent_id, "knowledge_engineer", "Let's build robust knowledge graph solutions.")


class KnowledgeGraphVPLead(SimpleResponderAgent):
    """Senior persona that distills complex queries into code snippets."""

    def __init__(self, agent_id: str = "kg_vp_lead"):
        super().__init__(agent_id, "knowledge_vp", "Provide a complex query to generate a code outline.")

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "complex_query":
            query = message.content.get("query", "")
            distilled = f"Distilled code instructions for '{query}'."
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"summary": distilled},
                timestamp=message.timestamp,
                message_type="complex_query_response",
            )
        return await super().process_message(message)
