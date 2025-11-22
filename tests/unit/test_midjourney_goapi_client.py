import asyncio
import json
import os
from typing import Any

import pytest

from semant.agent_tools.midjourney.goapi_client import GoAPIClient, GoAPIClientError


@pytest.mark.asyncio
async def test_imagine_validates_v7_reference_params(monkeypatch):
    monkeypatch.setenv("MIDJOURNEY_API_TOKEN", "test-token")

    client = GoAPIClient()
    # v7 should reject cref/cw
    with pytest.raises(GoAPIClientError):
        await client.imagine(prompt="p", model_version="v7", cref="http://x", cw=1)

    # v6 should reject oref/ow
    with pytest.raises(GoAPIClientError):
        await client.imagine(prompt="p", model_version="v6", oref="http://x", ow=1)


@pytest.mark.asyncio
async def test_action_parsing(monkeypatch):
    monkeypatch.setenv("MIDJOURNEY_API_TOKEN", "test-token")

    client = GoAPIClient()
    # Access protected helper via public API path
    task_type, index = client._parse_action("upscale2")
    assert task_type == "upscale"
    assert index == "2"


@pytest.mark.asyncio
async def test_imagine_success_with_mocked_http(monkeypatch):
    monkeypatch.setenv("MIDJOURNEY_API_TOKEN", "test-token")

    captured = {}

    class DummyResponse:
        def __init__(self, status_code: int, json_data: Any):
            self.status_code = status_code
            self._json_data = json_data
            self.text = json.dumps(json_data)

        def raise_for_status(self):
            if self.status_code >= 400:
                raise AssertionError("HTTP error raised in dummy")

        def json(self):
            return self._json_data

    async def dummy_post(url, headers=None, **kwargs):
        captured["url"] = url
        captured["headers"] = headers
        captured["kwargs"] = kwargs
        return DummyResponse(200, {"data": {"task_id": "abc123"}})

    # Patch httpx.AsyncClient to use dummy_post
    import httpx

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

    client = GoAPIClient()
    result = await client.imagine(prompt="hello", model_version="v7", oref="http://img", ow=5)
    assert result["data"]["task_id"] == "abc123"
    assert captured["url"].endswith("/task")
    assert captured["headers"]["Authorization"].startswith("Bearer ")


