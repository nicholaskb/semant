from __future__ import annotations

from typing import Any, Dict, Optional

from semant.agent_tools.midjourney.goapi_client import GoAPIClient
from semant.agent_tools.midjourney.kg_logging import KGLogger


class SeedTool:
    """Wrapper around GoAPIClient.seed with KG logging."""

    def __init__(self, client: Optional[GoAPIClient] = None, logger: Optional[KGLogger] = None, *, agent_id: str = "agent/SeedRunner") -> None:
        self.client = client or GoAPIClient()
        self.kg_logger = logger or KGLogger(agent_id=agent_id)

    async def run(self, *, origin_task_id: str) -> Dict[str, Any]:
        response = await self.client.seed(origin_task_id=origin_task_id)

        await self.kg_logger.log_tool_call(
            tool_name="mj.seed",
            inputs={"origin_task_id": origin_task_id},
            outputs=response,
            goapi_task=response,
            images=[],
        )

        return response


