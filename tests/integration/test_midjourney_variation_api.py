import json
import os
import pytest

from fastapi.testclient import TestClient
import main


@pytest.fixture
def client():
    return TestClient(main.app)


class DummyResponse:
    def __init__(self, status_code: int, json_data, content: bytes = b"PNG"):
        self.status_code = status_code
        self._json_data = json_data
        self.text = json.dumps(json_data)
        self.content = content
        self.is_success = status_code < 400

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError("HTTP error")

    def json(self):
        return self._json_data


@pytest.mark.asyncio
async def test_variation_endpoint(monkeypatch, client):
    monkeypatch.setenv("MIDJOURNEY_API_TOKEN", "test-token")

    import httpx

    async def dummy_post(url, headers=None, **kwargs):
        payload = kwargs.get("json", {})
        tt = payload.get("task_type")
        if tt == "variation":
            return DummyResponse(200, {"data": {"task_id": "var-1"}})
        return DummyResponse(200, {"data": {"task_id": "other"}})

    async def dummy_get(url, headers=None, **kwargs):
        return DummyResponse(200, {"data": {"id": url.rsplit("/", 1)[-1], "status": "completed", "output": {"image_url": "https://img.remote/url.png"}}})

    class DummyClient:
        def __init__(self, timeout=None):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, **kwargs):
            return await dummy_post(url, headers=headers, **kwargs)

        async def get(self, url, headers=None, **kwargs):
            return await dummy_get(url, headers=headers, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)

    import semant.agent_tools.midjourney.tools.gcs_mirror_tool as gcs_mod

    def fake_upload(source, dest):
        return f"https://storage.googleapis.com/fake_bucket/{dest}"

    async def fake_verify(url, timeout=60, interval=3):
        return True

    monkeypatch.setattr(gcs_mod, "upload_to_gcs_and_get_public_url", fake_upload)
    monkeypatch.setattr(gcs_mod, "verify_image_is_public", fake_verify)

    r = client.post("/api/midjourney/variation", json={"origin_task_id": "t-1", "index": 2})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["task_id"] == "var-1"
    assert d["gcs_url"].startswith("https://storage.googleapis.com/")


