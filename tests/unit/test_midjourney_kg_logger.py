import asyncio
import pytest

from semant.agent_tools.midjourney.kg_logging import KGLogger, _extract_task_id
from kg.models.graph_manager import KnowledgeGraphManager


@pytest.mark.asyncio
async def test_kg_logger_logs_tool_call_and_task_link():
    kg = KnowledgeGraphManager()
    logger = KGLogger(kg=kg, agent_id="agent/TestAgent")

    outputs = {"data": {"task_id": "t123"}}
    uris = await logger.log_tool_call(
        tool_name="mj.imagine",
        inputs={"prompt": "hello"},
        outputs=outputs,
        goapi_task=outputs,
        images=["https://example.com/i.png"],
    )

    assert "call_uri" in uris and uris["call_uri"]
    assert "task_uri" in uris and uris["task_uri"].endswith("t123")


def test_extract_task_id_variants():
    assert _extract_task_id({"data": {"task_id": "x"}}) == "x"
    assert _extract_task_id({"task_id": "y"}) == "y"
    assert _extract_task_id({"id": "z"}) == "z"
    assert _extract_task_id(None) is None


