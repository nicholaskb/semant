from __future__ import annotations

from typing import Any, Dict, Optional

from semant.agent_tools.midjourney.goapi_client import GoAPIClient
from semant.agent_tools.midjourney.kg_logging import KGLogger


class DescribeTool:
    """Wrapper around GoAPIClient.describe with KG logging."""

    def __init__(self, client: Optional[GoAPIClient] = None, logger: Optional[KGLogger] = None, *, agent_id: str = "agent/DescribeRunner") -> None:
        self.client = client or GoAPIClient()
        self.kg_logger = logger or KGLogger(agent_id=agent_id)

    async def run(self, *, image_url: str) -> Dict[str, Any]:
        response = await self.client.describe(image_url=image_url)

        images = []
        if isinstance(image_url, str) and image_url.startswith("http"):
            images.append(image_url)

        await self.kg_logger.log_tool_call(
            tool_name="mj.describe",
            inputs={"image_url": image_url},
            outputs=response,
            goapi_task=response,
            images=images,
        )

        return response


