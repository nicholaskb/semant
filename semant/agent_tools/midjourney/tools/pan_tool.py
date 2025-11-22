from __future__ import annotations

from typing import Any, Dict, Optional

from semant.agent_tools.midjourney.goapi_client import GoAPIClient
from semant.agent_tools.midjourney.kg_logging import KGLogger


class PanTool:
    def __init__(self, client: Optional[GoAPIClient] = None, logger: Optional[KGLogger] = None, *, agent_id: str = "agent/PanRunner") -> None:
        self.client = client or GoAPIClient()
        self.kg_logger = logger or KGLogger(agent_id=agent_id)

    async def run(self, *, origin_task_id: str, direction: str) -> Dict[str, Any]:
        response = await self.client.pan(origin_task_id=origin_task_id, direction=direction)
        await self.kg_logger.log_tool_call(
            tool_name="mj.pan",
            inputs={"origin_task_id": origin_task_id, "direction": direction},
            outputs=response,
            goapi_task=response,
            images=[],
        )
        return response


