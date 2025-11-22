import pytest

from semant.agent_tools.midjourney.goapi_client import GoAPIClient, GoAPIClientError


@pytest.mark.asyncio
async def test_inpaint_outpaint_url_validation(monkeypatch):
    monkeypatch.setenv("MIDJOURNEY_API_TOKEN", "t")
    c = GoAPIClient()
    with pytest.raises(GoAPIClientError):
        await c.inpaint(image_url="not-a-url", mask_url="http://mask")
    with pytest.raises(GoAPIClientError):
        await c.inpaint(image_url="http://img", mask_url="nope")
    with pytest.raises(GoAPIClientError):
        await c.outpaint(image_url="nope")


@pytest.mark.asyncio
async def test_pan_zoom_validation(monkeypatch):
    monkeypatch.setenv("MIDJOURNEY_API_TOKEN", "t")
    c = GoAPIClient()
    with pytest.raises(GoAPIClientError):
        await c.pan(origin_task_id="x", direction="forward")
    with pytest.raises(GoAPIClientError):
        await c.zoom(origin_task_id="x", factor=0)
    with pytest.raises(GoAPIClientError):
        await c.zoom(origin_task_id="x", factor="abc")


