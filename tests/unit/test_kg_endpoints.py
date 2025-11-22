import asyncio
from fastapi.testclient import TestClient

import main as main_mod
from semant.agent_tools.midjourney.kg_logging import MJ_NS, CORE_NS, SCHEMA_NS


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def test_kg_uploads_endpoint_lists_uploaded_images():
    client = TestClient(main_mod.app)
    kg = main_mod._kg_manager

    async def setup_kg():
        await kg.initialize()
        call_uri = f"{MJ_NS}ToolCall/test-upload"
        media_uri = f"{SCHEMA_NS}ImageObject/testimg"
        url = "https://example.com/img.png"
        await kg.add_triple(call_uri, f"{CORE_NS}type", f"{MJ_NS}ToolCall")
        await kg.add_triple(call_uri, f"{CORE_NS}name", "mj.upload_image")
        await kg.add_triple(media_uri, f"{CORE_NS}type", f"{SCHEMA_NS}ImageObject")
        await kg.add_triple(media_uri, f"{SCHEMA_NS}contentUrl", url)
        await kg.add_triple(call_uri, f"{SCHEMA_NS}associatedMedia", media_uri)

    _run(setup_kg())

    resp = client.get("/api/midjourney/kg/uploads")
    assert resp.status_code == 200
    data = resp.json()
    assert any(row.get("url") == "https://example.com/img.png" for row in data)


def test_kg_trace_endpoint_returns_tool_calls_for_task():
    client = TestClient(main_mod.app)
    kg = main_mod._kg_manager

    async def setup_kg():
        await kg.initialize()
        task_id = "task-123"
        task_uri = f"{MJ_NS}Task/{task_id}"
        call_uri = f"{MJ_NS}ToolCall/trace1"
        media_uri = f"{SCHEMA_NS}ImageObject/traceimg"
        await kg.add_triple(call_uri, f"{CORE_NS}type", f"{MJ_NS}ToolCall")
        await kg.add_triple(call_uri, f"{CORE_NS}name", "mj.imagine")
        await kg.add_triple(task_uri, f"{CORE_NS}type", f"{MJ_NS}Task")
        await kg.add_triple(call_uri, f"{CORE_NS}relatedTo", task_uri)
        await kg.add_triple(call_uri, f"{MJ_NS}input", '{"prompt":"a fox"}')
        await kg.add_triple(call_uri, f"{MJ_NS}output", '{"ok":true}')
        await kg.add_triple(media_uri, f"{CORE_NS}type", f"{SCHEMA_NS}ImageObject")
        await kg.add_triple(media_uri, f"{SCHEMA_NS}contentUrl", "https://example.com/trace.png")
        await kg.add_triple(call_uri, f"{SCHEMA_NS}associatedMedia", media_uri)

    _run(setup_kg())

    resp = client.get("/api/midjourney/kg/trace/task-123")
    assert resp.status_code == 200
    data = resp.json()
    assert any(row.get("name") == "mj.imagine" for row in data)

