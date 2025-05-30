import pytest
from fastapi.testclient import TestClient
from main_api import app

client = TestClient(app)

def test_chat_endpoint():
    # Test the chat endpoint with a simple message
    response = client.post(
        "/chat",
        json={"message": "Hello", "history": []}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "history" in data
    assert "agent" in data
    assert data["agent"] == "MainAgent"
    assert len(data["history"]) == 1
    assert data["history"][0] == "Hello"

def test_chat_with_history():
    # Test the chat endpoint with existing history
    history = ["Hello", "How are you?"]
    response = client.post(
        "/chat",
        json={"message": "I'm good", "history": history}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) == 3
    assert data["history"][-1] == "I'm good"

def test_chat_help_message():
    # Test the help message response
    response = client.post(
        "/chat",
        json={"message": "help", "history": ["Hello"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "assist" in data["response"].lower() 