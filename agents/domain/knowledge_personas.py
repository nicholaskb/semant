from typing import Any, Dict
from agents.core.base_agent import BaseAgent, AgentMessage
from .simple_agents import SimpleResponderAgent
import uuid
from datetime import datetime


class KnowledgeGraphConsultant(SimpleResponderAgent):
    """Persona offering general knowledge graph consulting advice."""

    def __init__(self, agent_id: str = "kg_consultant", **kwargs):
        super().__init__(agent_id, "knowledge_consultant", "I can help design and query your knowledge graph.")


class OpenAIKnowledgeGraphEngineer(SimpleResponderAgent):
    """Persona focused on engineering best practices for knowledge graphs."""

    def __init__(self, agent_id: str = "kg_engineer", **kwargs):
        super().__init__(agent_id, "knowledge_engineer", "Let's build robust knowledge graph solutions.")


class KnowledgeGraphVPLead(SimpleResponderAgent):
    """Senior persona that distills complex queries into code snippets."""

    def __init__(self, agent_id: str = "kg_vp_lead", **kwargs):
        super().__init__(agent_id, "knowledge_vp", "Provide a complex query to generate a code outline.")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "complex_query":
            query = message.content.get("query", "")
            distilled = f"Distilled code instructions for '{query}'."
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"summary": distilled},
                timestamp=datetime.utcnow(),
                message_type="complex_query_response",
            )
        return await super()._process_message_impl(message)
