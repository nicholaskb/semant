from __future__ import annotations

from typing import Any, Dict, Optional, List

from semant.agent_tools.midjourney.goapi_client import GoAPIClient
from semant.agent_tools.midjourney.kg_logging import KGLogger


class BlendTool:
    """Wrapper around GoAPIClient.blend with KG logging."""

    def __init__(self, client: Optional[GoAPIClient] = None, logger: Optional[KGLogger] = None, *, agent_id: str = "agent/BlendRunner") -> None:
        self.client = client or GoAPIClient()
        self.kg_logger = logger or KGLogger(agent_id=agent_id)

    async def run(self, *, image_urls: List[str], dimension: str) -> Dict[str, Any]:
        response = await self.client.blend(image_urls=image_urls, dimension=dimension)

        images = [u for u in (image_urls or []) if isinstance(u, str) and u.startswith("http")]

        await self.kg_logger.log_tool_call(
            tool_name="mj.blend",
            inputs={"image_urls": image_urls, "dimension": dimension},
            outputs=response,
            goapi_task=response,
            images=images,
        )

        return response


