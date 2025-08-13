"""
Unified Asynchronous GoAPI Client for Kontext.

This mirrors the Midjourney client but targets a generic "Kontext" model API
via GoAPI's /task endpoints. It implements robust error handling, retry with
exponential backoff for 429/5xx, and helpers for GCS uploads.
"""
from __future__ import annotations

import asyncio
import os
import logging
from typing import Any, Dict, Optional, List
from pathlib import Path
from io import BytesIO

import httpx
from google.cloud import storage

from config.settings import settings


logger = logging.getLogger(__name__)

__all__ = [
    "KontextClient",
    "KontextError",
    "upload_to_gcs_and_get_public_url",
    "poll_until_complete",
]


class KontextError(RuntimeError):
    """Raised when the Kontext GoAPI request fails."""


def upload_to_gcs_and_get_public_url(
    source: Path | bytes, destination_blob_name: str, content_type: str = "image/png"
) -> str:
    """Upload local file or bytes to GCS and return public URL."""
    bucket_name = settings.GCS_BUCKET_NAME
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME is not configured in settings.")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    if isinstance(source, Path):
        blob.upload_from_filename(str(source), timeout=300, content_type=content_type)
    else:
        blob.upload_from_string(source, timeout=300, content_type=content_type)

    blob.make_public()
    return blob.public_url


class KontextClient:
    """Async client for Kontext over GoAPI PPU."""

    _BASE_URL = os.getenv("GOAPI_BASE_URL", "https://api.goapi.ai/api/v1")
    _TASK_ENDPOINT = f"{_BASE_URL}/task"

    def __init__(self, api_token: Optional[str] = None, timeout: float = 120.0):
        self._api_token = api_token or os.getenv("KONTEXT_API_TOKEN")
        if not self._api_token:
            raise ValueError(
                "KONTEXT_API_TOKEN not provided via parameter or environment variable"
            )
        self._timeout = httpx.Timeout(timeout)

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, url: str, *, json: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """HTTP request with retry/backoff for 429/5xx."""
        max_retries = 5
        backoff = 1.0
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(max_retries):
                try:
                    resp = await client.request(method, url, headers=self._headers, json=json)
                    if resp.status_code in (429, 500, 502, 503, 504):
                        raise httpx.HTTPStatusError("Retryable status", request=resp.request, response=resp)
                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPStatusError as e:
                    status = e.response.status_code if e.response else None
                    if status in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                        logger.warning("Kontext GoAPI status %s – retrying in %.1fs", status, backoff)
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    logger.error("Kontext GoAPI request failed: %s %s", status, e)
                    raise
                except httpx.RequestError as e:
                    if attempt < max_retries - 1:
                        logger.warning("Network error – retrying in %.1fs (%s)", backoff, e)
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    raise

    async def submit_generate(
        self,
        prompt: str,
        *,
        aspect_ratio: Optional[str] = None,
        process_mode: Optional[str] = None,
        image_url: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Submit a generation task.

        The "model" and exact fields depend on the Kontext API behind GoAPI. We
        mirror the Midjourney shape so the server and UI patterns can be reused.
        """
        payload: Dict[str, Any] = {
            "model": "kontext",          # service identifier on GoAPI side
            "task_type": "generate",     # generic task name
            "input": {
                "prompt": prompt,
            },
        }
        if process_mode:
            payload["input"]["process_mode"] = process_mode
        if aspect_ratio:
            payload["input"]["aspect_ratio"] = aspect_ratio
        if image_url:
            payload["input"]["image_url"] = image_url
        if extras:
            payload["input"].update(extras)

        return await self._request("POST", self._TASK_ENDPOINT, json=payload)

    async def submit_action(self, origin_task_id: str, *, action: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": "kontext",
            "task_type": action,
            "input": {"origin_task_id": origin_task_id},
        }
        return await self._request("POST", self._TASK_ENDPOINT, json=payload)

    async def poll_task(self, task_id: str) -> Dict[str, Any]:
        url = f"{self._TASK_ENDPOINT}/{task_id}"
        return await self._request("GET", url)


async def poll_until_complete(client: KontextClient, task_id: str, interval: int = 5, max_wait: int = 900) -> Dict[str, Any]:
    """Poll the task until finished/failed/timeout and return final JSON."""
    elapsed = 0
    while elapsed < max_wait:
        result = await client.poll_task(task_id)
        data = result.get("data", result)
        status = data.get("status")
        if status in {"completed", "finished"}:
            return data
        if status in {"failure", "failed", "error"}:
            raise KontextError(f"Task failed: {data}")
        await asyncio.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"Task {task_id} did not complete after {max_wait}s")


