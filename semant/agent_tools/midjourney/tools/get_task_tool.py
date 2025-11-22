from __future__ import annotations

from typing import Any, Dict, Optional

from semant.agent_tools.midjourney.goapi_client import GoAPIClient
from semant.agent_tools.midjourney.kg_logging import KGLogger


class GetTaskTool:
    """Wrapper for GoAPIClient.get_task with KG logging (read-only)."""

    def __init__(self, client: Optional[GoAPIClient] = None, logger: Optional[KGLogger] = None, *, agent_id: str = "agent/GetTaskRunner") -> None:
        self.client = client or GoAPIClient()
        self.kg_logger = logger or KGLogger(agent_id=agent_id)

    async def run(self, *, task_id: str) -> Dict[str, Any]:
        response = await self.client.get_task(task_id=task_id)

        # Attempt to extract image URLs from the status payload
        images = []
        try:
            data = response.get("data", response)
            output = data.get("output", {}) if isinstance(data, dict) else {}
            # common keys
            for key in ("image_url", "image", "url"):
                val = output.get(key)
                if isinstance(val, str) and val.startswith("http"):
                    images.append(val)
            # optional multiple urls
            temp_imgs = output.get("temporary_image_urls")
            if isinstance(temp_imgs, list):
                images.extend([u for u in temp_imgs if isinstance(u, str) and u.startswith("http")])
        except Exception:
            images = []

        await self.kg_logger.log_tool_call(
            tool_name="mj.get_task",
            inputs={"task_id": task_id},
            outputs=response,
            goapi_task=response,
            images=images,
        )

        return response


