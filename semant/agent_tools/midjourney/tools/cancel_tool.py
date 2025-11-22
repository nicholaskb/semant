from __future__ import annotations

from typing import Any, Dict, Optional

from semant.agent_tools.midjourney.goapi_client import GoAPIClient
from semant.agent_tools.midjourney.kg_logging import KGLogger


class CancelTool:
    """Wrapper for GoAPIClient.cancel_task with KG logging.

    Note: underlying cancel path may vary across providers. This uses the
    client's current generic cancel implementation and should be updated when
    a canonical endpoint is confirmed.
    """

    def __init__(self, client: Optional[GoAPIClient] = None, logger: Optional[KGLogger] = None, *, agent_id: str = "agent/CancelRunner") -> None:
        self.client = client or GoAPIClient()
        self.kg_logger = logger or KGLogger(agent_id=agent_id)

    async def run(self, *, task_id: str) -> Dict[str, Any]:
        response = await self.client.cancel_task(task_id=task_id)

        await self.kg_logger.log_tool_call(
            tool_name="mj.cancel",
            inputs={"task_id": task_id},
            outputs=response,
            goapi_task=response,
            images=[],
        )

        return response


