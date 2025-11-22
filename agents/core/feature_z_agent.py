from agents.core.base_agent import BaseAgent, AgentMessage
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
from agents.core.message_types import AgentMessage

class FeatureZAgent(BaseAgent):
    """
    Agent that implements Feature Z.
    Message content should include {'feature_data': ...}
    """
    def __init__(
        self,
        agent_id: str = "feature_z_agent",
        capabilities: Optional[List[str]] = None,
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="feature_z",
            capabilities=capabilities,
            knowledge_graph=knowledge_graph,
            config=config
        )

    async def initialize(self) -> None:
        self.logger.info("Feature Z Agent initialized")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        feature_data = message.content.get('feature_data')
        if not feature_data:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"error": "No feature data provided."},
                timestamp=message.timestamp,
                message_type="feature_z_response"
            )
        try:
            # Implement the logic for Feature Z here
            self.logger.info(f"Processing feature data: {feature_data}")
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "Feature Z processed successfully."},
                timestamp=message.timestamp,
                message_type="feature_z_response"
            )
        except Exception as e:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"error": str(e)},
                timestamp=message.timestamp,
                message_type="feature_z_response"
            )

    async def query_knowledge_graph(self, query: dict) -> dict:
        return {}

    async def update_knowledge_graph(self, update_data: dict) -> None:
        """Feature Z does not touch the knowledge graph in this demo."""
        return

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

        pass 