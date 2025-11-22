from __future__ import annotations

from typing import Any, Dict, Optional

from semant.agent_tools.midjourney.goapi_client import GoAPIClient
from semant.agent_tools.midjourney.kg_logging import KGLogger


class ImagineTool:
    """Wrapper around GoAPIClient.imagine with KG logging."""

    def __init__(self, client: Optional[GoAPIClient] = None, logger: Optional[KGLogger] = None, *, agent_id: str = "agent/ImagineRunner") -> None:
        self.client = client or GoAPIClient()
        self.kg_logger = logger or KGLogger(agent_id=agent_id)

    async def run(
        self,
        *,
        prompt: str,
        model_version: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        process_mode: Optional[str] = None,
        cref: Optional[str] = None,
        cw: Optional[int] = None,
        oref: Optional[str] = None,
        ow: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        response = await self.client.imagine(
            prompt=prompt,
            model_version=model_version,
            aspect_ratio=aspect_ratio,
            process_mode=process_mode,
            cref=cref,
            cw=cw,
            oref=oref,
            ow=ow,
            extra=extra,
        )

        # Attempt to extract any image URLs if present in response (best-effort)
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
            tool_name="mj.imagine",
            inputs={
                "prompt": prompt,
                "model_version": model_version,
                "aspect_ratio": aspect_ratio,
                "process_mode": process_mode,
                "cref": cref,
                "cw": cw,
                "oref": oref,
                "ow": ow,
                "extra": extra or {},
            },
            outputs=response,
            goapi_task=response,
            images=images,
        )

        return response


