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
        # Provide binary content for cases where code reads resp.content (image download)
        self.content = b"PNG"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError("HTTP error")

    def json(self):
        return self._json_data


@pytest.mark.asyncio
async def test_imagine_and_mirror_endpoint(monkeypatch, client):
    # Ensure token is set
    monkeypatch.setenv("MIDJOURNEY_API_TOKEN", "test-token")

    # Mock httpx AsyncClient used by agent tools
    import httpx

    async def dummy_post(url, headers=None, **kwargs):
        payload = kwargs.get("json", {})
        tt = payload.get("task_type")
        if tt == "imagine":
            return DummyResponse(200, {"data": {"task_id": "t-123", "output": {"image_url": "https://img.remote/url.png"}}})
        # Default action/others
        return DummyResponse(200, {"data": {"task_id": "action-1"}})

    async def dummy_get(url, headers=None, **kwargs):
        # Always return completed status for polling
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

    # Mock GCS upload helpers in the mirror tool module
    import semant.agent_tools.midjourney.tools.gcs_mirror_tool as gcs_mod

    def fake_upload(source, dest):
        return f"https://storage.googleapis.com/fake_bucket/{dest}"

    async def fake_verify(url, timeout=60, interval=3):
        return True

    monkeypatch.setattr(gcs_mod, "upload_to_gcs_and_get_public_url", fake_upload)
    monkeypatch.setattr(gcs_mod, "verify_image_is_public", fake_verify)

    # Call the endpoint
    resp = client.post(
        "/api/midjourney/imagine-and-mirror",
        data={
            "prompt": "a minimalist watercolor fox, soft palette",
            "version": "v7",
            "interval": 0.1,
            "timeout": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["task_id"] == "t-123"
    assert data["image_url"].startswith("https://img.remote/")
    assert data["gcs_url"].startswith("https://storage.googleapis.com/")


