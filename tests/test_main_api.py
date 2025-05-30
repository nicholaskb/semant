from fastapi.testclient import TestClient
from main_api import app

client = TestClient(app)

def test_investigate():
    response = client.post("/investigate", json={"topic": "AI in healthcare"})
    assert response.status_code == 200
    data = response.json()
    assert "topic" in data
    assert data["topic"] == "AI in healthcare"

def test_traverse():
    response = client.post("/traverse", json={"start_node": "http://example.org/test/node1", "max_depth": 2})
    assert response.status_code == 200
    data = response.json()
    assert "start_node" in data
    assert data["start_node"] == "http://example.org/test/node1"

def test_feedback():
    response = client.post("/feedback", json={"feedback": "This is a test feedback."})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "received"
    assert data["feedback"] == "This is a test feedback." 