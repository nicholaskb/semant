import pytest

from agents.domain.planner_agent import PlannerAgent
from agents.core.base_agent import AgentMessage


class DummyRegistry:
    async def get_agent(self, name: str):
        raise RuntimeError("Should not be called in midjourney test branch")


@pytest.mark.asyncio
async def test_planner_midjourney_branch(monkeypatch):
    # Force availability toggle and stub the workflow
    import agents.domain.planner_agent as planner_mod

    monkeypatch.setattr(planner_mod, "_MJ_AVAILABLE", True, raising=False)

    async def fake_imagine_then_mirror(**kwargs):
        return {"task_id": "t-1", "image_url": "https://r", "gcs_url": "https://g"}

    monkeypatch.setattr(planner_mod, "imagine_then_mirror", fake_imagine_then_mirror, raising=False)

    planner = PlannerAgent("planner", DummyRegistry())
    await planner.initialize()
    msg = AgentMessage(
        sender_id="test",
        recipient_id="planner",
        content={
            "prompt": "a test",
            "midjourney": {"version": "v7", "interval": 0.01, "timeout": 1},
        },
        message_type="request",
    )
    result = await planner.process_message(msg)
    assert "midjourney" in result.content
    assert result.content["midjourney"]["task_id"] == "t-1"

