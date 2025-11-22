import time

from agents.core.base_agent import BaseAgent
from rdflib import Graph


class _KGWrapper:
    def __init__(self):
        self.graph = Graph()

    def __getattr__(self, item):
        return getattr(self.graph, item)


class PerfAgent(BaseAgent):
    async def _process_message_impl(self, message):
        raise NotImplementedError

    def __init__(self):
        super().__init__(agent_id="perf", knowledge_graph=_KGWrapper())


def test_write_diary_performance():
    agent = PerfAgent()
    N = 500  # number of writes
    start = time.perf_counter()
    for i in range(N):
        agent.write_diary(f"entry {i}")
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / N) * 1000
    assert avg_ms <= 5, f"Diary write too slow: {avg_ms:.2f} ms > 5 ms budget" 