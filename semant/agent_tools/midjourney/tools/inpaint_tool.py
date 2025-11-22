from __future__ import annotations

from typing import Any, Dict, Optional

from semant.agent_tools.midjourney.goapi_client import GoAPIClient
from semant.agent_tools.midjourney.kg_logging import KGLogger


class InpaintTool:
    def __init__(self, client: Optional[GoAPIClient] = None, logger: Optional[KGLogger] = None, *, agent_id: str = "agent/InpaintRunner") -> None:
        self.client = client or GoAPIClient()
        self.kg_logger = logger or KGLogger(agent_id=agent_id)

    async def run(self, *, image_url: str, mask_url: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        response = await self.client.inpaint(image_url=image_url, mask_url=mask_url, prompt=prompt)

        images = [u for u in (image_url, mask_url) if isinstance(u, str) and u.startswith("http")]
        await self.kg_logger.log_tool_call(
            tool_name="mj.inpaint",
            inputs={"image_url": image_url, "mask_url": mask_url, "prompt": prompt},
            outputs=response,
            goapi_task=response,
            images=images,
        )
        return response


