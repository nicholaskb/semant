import json
import os
import pytest

from fastapi.testclient import TestClient
import main


@pytest.fixture
def client():
    return TestClient(main.app)


class DummyResponse:
    def __init__(self, status_code: int, json_data):
        self.status_code = status_code
        self._json_data = json_data
        self.text = json.dumps(json_data)
        self.is_success = status_code < 400

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError("HTTP error")

    def json(self):
        return self._json_data


@pytest.mark.asyncio
async def test_cancel_endpoint(monkeypatch, client):
    monkeypatch.setenv("MIDJOURNEY_API_TOKEN", "test-token")

    import httpx

    async def dummy_post(url, headers=None, **kwargs):
        payload = kwargs.get("json", {})
        tt = payload.get("task_type")
        if tt == "cancel":
            return DummyResponse(200, {"status": "ok", "data": {"task_id": payload.get("input", {}).get("task_id"), "cancelled": True}})
        return DummyResponse(200, {"data": {"task_id": "other"}})

    class DummyClient:
        def __init__(self, timeout=None):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, **kwargs):
            return await dummy_post(url, headers=headers, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)

    r = client.post("/api/midjourney/cancel", json={"task_id": "t-1"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("status") == "ok"
    assert d.get("data", {}).get("cancelled") is True


