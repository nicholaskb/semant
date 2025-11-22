import json
import pytest

from semant.agent_tools.midjourney.tools.describe_tool import DescribeTool
from semant.agent_tools.midjourney.tools.seed_tool import SeedTool


@pytest.mark.asyncio
async def test_describe_tool_runs_and_logs(monkeypatch):
    import httpx

    class DummyResponse:
        def __init__(self, status_code: int, json_data):
            self.status_code = status_code
            self._json_data = json_data
            self.text = json.dumps(json_data)

        def raise_for_status(self):
            if self.status_code >= 400:
                raise AssertionError("HTTP error")

        def json(self):
            return self._json_data

    async def dummy_post(url, headers=None, **kwargs):
        return DummyResponse(200, {"data": {"task_id": "d1", "output": {"text": "desc"}}})

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
    monkeypatch.setenv("MIDJOURNEY_API_TOKEN", "t")

    tool = DescribeTool()
    resp = await tool.run(image_url="https://img")
    assert resp["data"]["task_id"] == "d1"


@pytest.mark.asyncio
async def test_seed_tool_runs_and_logs(monkeypatch):
    import httpx

    class DummyResponse:
        def __init__(self, status_code: int, json_data):
            self.status_code = status_code
            self._json_data = json_data
            self.text = json.dumps(json_data)

        def raise_for_status(self):
            if self.status_code >= 400:
                raise AssertionError("HTTP error")

        def json(self):
            return self._json_data

    async def dummy_post(url, headers=None, **kwargs):
        return DummyResponse(200, {"data": {"task_id": "s1"}})

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
    monkeypatch.setenv("MIDJOURNEY_API_TOKEN", "t")

    tool = SeedTool()
    resp = await tool.run(origin_task_id="xyz")
    assert resp["data"]["task_id"] == "s1"


