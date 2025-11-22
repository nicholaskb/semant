import json
import pytest

from semant.agent_tools.midjourney.tools.inpaint_tool import InpaintTool
from semant.agent_tools.midjourney.tools.outpaint_tool import OutpaintTool
from semant.agent_tools.midjourney.tools.pan_tool import PanTool
from semant.agent_tools.midjourney.tools.zoom_tool import ZoomTool


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


@pytest.mark.asyncio
async def test_inpaint_tool(monkeypatch):
    import httpx

    async def dummy_post(url, headers=None, **kwargs):
        return DummyResponse(200, {"data": {"task_id": "ip1"}})

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

    tool = InpaintTool()
    resp = await tool.run(image_url="https://img", mask_url="https://mask", prompt="fix")
    assert resp["data"]["task_id"] == "ip1"


@pytest.mark.asyncio
async def test_outpaint_tool(monkeypatch):
    import httpx

    async def dummy_post(url, headers=None, **kwargs):
        return DummyResponse(200, {"data": {"task_id": "op1"}})

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

    tool = OutpaintTool()
    resp = await tool.run(image_url="https://img", prompt="extend")
    assert resp["data"]["task_id"] == "op1"


@pytest.mark.asyncio
async def test_pan_tool(monkeypatch):
    import httpx

    async def dummy_post(url, headers=None, **kwargs):
        return DummyResponse(200, {"data": {"task_id": "pan1"}})

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

    tool = PanTool()
    resp = await tool.run(origin_task_id="t1", direction="right")
    assert resp["data"]["task_id"] == "pan1"


@pytest.mark.asyncio
async def test_zoom_tool(monkeypatch):
    import httpx

    async def dummy_post(url, headers=None, **kwargs):
        return DummyResponse(200, {"data": {"task_id": "zoom1"}})

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

    tool = ZoomTool()
    resp = await tool.run(origin_task_id="t1", factor=1.5)
    assert resp["data"]["task_id"] == "zoom1"


