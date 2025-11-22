from fastapi.testclient import TestClient

from main import app
from agents.core.data_handler_agent import SensorAgent

client = TestClient(app)


def test_static_diary_viewer_served():
    resp = client.get("/static/diary_viewer.html")
    assert resp.status_code == 200
    assert b"Agent Diary Viewer" in resp.content


def test_diary_endpoint_returns_entries():
    agent_id = "viewer_test_agent"
    # Create and register agent
    from rdflib import Graph
    agent = SensorAgent(agent_id=agent_id)
    # attach lightweight KG wrapper with .graph attribute
    class _KG:  # simple stub
        def __init__(self):
            self.graph = Graph()

    agent.knowledge_graph = _KG()
    import asyncio, nest_asyncio
    nest_asyncio.apply()
    asyncio.run(agent.initialize())
    agent.write_diary("hello world", details={"from": "test"})

    resp = client.get(f"/diary/{agent_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) >= 1
    assert any("hello world" in entry["message"] for entry in data)

    # Triples endpoint should also succeed (may be empty if no KG)
    resp2 = client.get(f"/diary/{agent_id}/triples")
    # 200 even if KG not attached (handled inside API)
    assert resp2.status_code == 200 