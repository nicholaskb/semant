from typing import Any, Dict, Optional, Set
from datetime import datetime

from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger
import uuid
from agents.core.capability_types import Capability, CapabilityType


class JudgeAgent(BaseAgent):
    """Agent that evaluates and makes decisions."""

    def __init__(
        self,
        agent_id: str,
        agent_type: str = "judge",
        capabilities: Optional[Set[Capability]] = None,
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        default_capabilities = {
            Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
            Capability(CapabilityType.DECISION_MAKING, "1.0")
        }
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities or default_capabilities,
            knowledge_graph=knowledge_graph,
            config=config
        )
        self._decisions = []
        self.logger = logger.bind(agent_id=agent_id)

    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Judge Agent initialized")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message."""
        if message.message_type == "evaluate":
            decision = await self.evaluate_challenge(message.content["data"])
            self._decisions.append({
                "timestamp": datetime.utcnow().isoformat(),
                "decision": decision
            })
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "success", "decision": decision},
                timestamp=datetime.utcnow(),
                message_type="evaluation_response"
            )
        else:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "error", "message": "Unknown message type"},
                timestamp=datetime.utcnow(),
                message_type="error"
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

        # Log the decision
        self._decisions.append({
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "data": challenge_data
        })

        return decision

    def get_decisions(self) -> list:
        """Get all decisions made by this agent."""
        return self._decisions

