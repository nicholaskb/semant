"""Minimal stub ScientificSwarmAgent required by AgentIntegrator tests.

The full implementation is not necessary for unit-test coverage; we only need
basic echo behaviour plus a default MESSAGE_PROCESSING capability so registry
lookups succeed.
"""

from typing import Optional, Set

from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.capability_types import Capability, CapabilityType


class ScientificSwarmAgent(BaseAgent):
    """Lightweight agent used exclusively by the test-suite."""

    def __init__(self, *args, **kwargs):
        """Flexible stub ctor to satisfy various test signatures.

        Accepted positional order in some tests: (agent_id, agent_type,
        capabilities, registry, knowledge_graph).  We only need agent_id and
        capabilities; the rest are ignored.
        """
        agent_id = args[0] if args else "scientific_swarm_stub"
        capabilities: Optional[Set[Capability]] = None
        if len(args) >= 3 and isinstance(args[2], set):
            capabilities = args[2]
        capabilities = capabilities or kwargs.get("capabilities")
        capabilities = capabilities or {Capability(CapabilityType.MESSAGE_PROCESSING)}

        super().__init__(
            agent_id=agent_id,
            agent_type="scientific_swarm",
            capabilities=capabilities,
            **kwargs,
        )

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:  # noqa: D401
        """Echo message content back to sender (sufficient for tests)."""
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"echo": message.content},
            message_type="response",
        )

    # Tests may introspect capability history
    async def get_capability_history(self):  # type: ignore[override]
        return []