import asyncio

import pytest
from rdflib import Graph

from agents.core.base_agent import BaseAgent, AgentMessage


class _KGWrapper:
    """Minimal wrapper exposing .graph attribute expected by BaseAgent.write_diary."""

    def __init__(self):
        self.graph = Graph()

    # Provide rdflib-like add/remove/query interfaces for convenience
    def __getattr__(self, item):
        return getattr(self.graph, item)


class EchoAgent(BaseAgent):
    """Simple agent that echoes messages – used for diary tests."""

    def __init__(self):
        super().__init__(
            agent_id="echo_test",
            knowledge_graph=_KGWrapper(),
            config={"auto_diary": True},
        )

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"echo": message.content},
        )


@pytest.mark.asyncio
async def test_auto_diary_and_triples():
    agent = EchoAgent()
    await agent.initialize()

    # Send a message and await response; auto-diary should record RECV & SEND
    response = await agent.process_message(
        AgentMessage(sender_id="tester", recipient_id="echo_test", content="Alice eats apples")
    )
    assert response.content["echo"] == "Alice eats apples"

    # Allow background triple insertion task to complete
    await asyncio.sleep(0.05)

    # Diary should have at least 2 entries (recv + send)
    diary_entries = agent.read_diary()
    assert len(diary_entries) >= 2, "Diary entries were not automatically recorded"

    # The KG should now contain triples derived from the diary sentence
    g = agent.knowledge_graph.graph  # type: ignore[attr-defined]
    triples = list(g.triples((None, None, None)))
    assert triples, "No triples found in knowledge graph"
    # Check that at least one predicate ends with core#eats (from sample message)
    assert any(str(p).endswith("eat") or str(p).endswith("eats") for _, p, _ in triples), "Expected predicate not found" 