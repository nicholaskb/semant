from __future__ import annotations

from typing import Any, Dict, Optional

from semant.agent_tools.midjourney.goapi_client import GoAPIClient
from semant.agent_tools.midjourney.kg_logging import KGLogger


class ActionTool:
    """Wrapper around GoAPIClient.action with KG logging."""

    def __init__(self, client: Optional[GoAPIClient] = None, logger: Optional[KGLogger] = None, *, agent_id: str = "agent/ActionRunner") -> None:
        self.client = client or GoAPIClient()
        self.kg_logger = logger or KGLogger(agent_id=agent_id)

    async def run(
        self,
        *,
        origin_task_id: str,
        action: str,
    ) -> Dict[str, Any]:
        response = await self.client.action(origin_task_id=origin_task_id, action=action)

        images = []
        try:
            data = response.get("data", response)
            output = data.get("output", {}) if isinstance(data, dict) else {}
            for key in ("image_url", "image", "url"):
                val = output.get(key)
                if isinstance(val, str) and val.startswith("http"):
                    images.append(val)
        except Exception:
            pass

        await self.kg_logger.log_tool_call(
            tool_name="mj.action",
            inputs={
                "origin_task_id": origin_task_id,
                "action": action,
            },
            outputs=response,
            goapi_task=response,
            images=images,
        )

        return response


