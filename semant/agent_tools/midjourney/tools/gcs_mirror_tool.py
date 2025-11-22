from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx

from semant.agent_tools.midjourney.kg_logging import KGLogger

# Reuse existing uploader from midjourney_integration
from midjourney_integration.client import upload_to_gcs_and_get_public_url, verify_image_is_public


class GCSMirrorTool:
    """Mirror a remote Midjourney image URL into GCS and log to the knowledge graph.

    This uses the existing `upload_to_gcs_and_get_public_url` helper from
    `midjourney_integration.client` to ensure consistent behavior and config usage.
    """

    def __init__(self, logger: Optional[KGLogger] = None, *, agent_id: str = "agent/GCSMirror") -> None:
        self.kg_logger = logger or KGLogger(agent_id=agent_id)

    async def run(self, *, source_url: str, task_id: str, filename: str = "image.png") -> Dict[str, Any]:
        # Download bytes from source_url
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(source_url)
            resp.raise_for_status()
            image_bytes = resp.content

        # Upload to GCS under midjourney/{task_id}/
        destination = f"midjourney/{task_id}/{filename}"
        gcs_url = upload_to_gcs_and_get_public_url(image_bytes, destination)

        # Verify public access (best-effort)
        try:
            await verify_image_is_public(gcs_url, timeout=60, interval=3)
        except Exception:
            # Non-fatal; continue even if verification loop times out
            pass

        output = {"gcs_url": gcs_url, "destination": destination}
        await self.kg_logger.log_tool_call(
            tool_name="mj.gcs_mirror",
            inputs={"source_url": source_url, "task_id": task_id, "destination": destination},
            outputs=output,
            goapi_task={"task_id": task_id},
            images=[gcs_url],
        )
        return output


