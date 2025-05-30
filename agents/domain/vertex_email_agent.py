from typing import Any, Dict, List
from agents.core.base_agent import BaseAgent, AgentMessage
from loguru import logger

class VertexEmailAgent(BaseAgent):
    """Agent that simulates sending email using Google Vertex AI."""

    def __init__(self, agent_id: str = "vertex_email_agent"):
        super().__init__(agent_id, "vertex_email")
        self.sent_emails: List[Dict[str, str]] = []
        self.logger = logger.bind(agent_id=agent_id)

    async def initialize(self) -> None:
        """Initialize the agent."""
        self.logger.info("Vertex Email Agent initialized (simulation)")

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "send_email":
            email = {
                "recipient": message.content.get("recipient"),
                "subject": message.content.get("subject"),
                "body": message.content.get("body"),
            }
            await self.send_email(**email)
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"status": "sent", **email},
                timestamp=message.timestamp,
                message_type="send_email_response",
            )
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"status": "error", "message": "Unknown message type"},
            timestamp=message.timestamp,
            message_type="error_response",
        )

    async def send_email(self, recipient: str, subject: str, body: str) -> None:
        """Simulate sending an email via Vertex AI."""
        self.logger.info(
            f"Simulated sending email to {recipient} with subject '{subject}'"
        )
        self.sent_emails.append(
            {"recipient": recipient, "subject": subject, "body": body}
        )
        self.write_diary(
            f"Sent email to {recipient} with subject '{subject}'",
            {"body": body},
        )
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph(
                {
                    f"email:{len(self.sent_emails)}": {
                        "recipient": recipient,
                        "subject": subject,
                        "body": body,
                    }
                }
            )

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph(update_data)

    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        if not self.knowledge_graph:
            return {}
        return await self.knowledge_graph.query_graph(query.get("sparql", ""))
