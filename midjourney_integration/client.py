"""
Unified Asynchronous GoAPI Midjourney Client.

This module provides a single, reliable async client for interacting with the 
GoAPI V1 endpoints for Midjourney. It replaces the previous combination of 
`goapi_generate.py` and the old `client.py`.
"""
from __future__ import annotations

import os
import asyncio
import logging
from typing import Any, Dict, Optional, List
import re
from pathlib import Path
from io import BytesIO

import httpx
from google.cloud import storage
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)

__all__ = ["MidjourneyClient", "MidjourneyError", "upload_to_gcs_and_get_public_url"]


class MidjourneyError(RuntimeError):
    """Raised when the Midjourney GoAPI returns an error status code."""


def upload_to_gcs_and_get_public_url(
    source: Path | bytes, destination_blob_name: str, content_type: str = "image/png"
) -> str:
    """
    Uploads a file or bytes to the GCS bucket and makes it public.
    This is now the single, unified uploader.
    """
    bucket_name = settings.GCS_BUCKET_NAME
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME is not configured in settings.")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    if isinstance(source, Path):
        logger.info("Uploading %s to gs://%s/%s", source, bucket_name, destination_blob_name)
        blob.upload_from_filename(str(source), timeout=300, content_type=content_type)
    else:
        logger.info("Uploading bytes to gs://%s/%s", bucket_name, destination_blob_name)
        blob.upload_from_string(source, timeout=300, content_type=content_type)

    blob.make_public()
    logger.info("File %s is now publicly available at %s", destination_blob_name, blob.public_url)
    return blob.public_url


async def verify_image_is_public(url: str, timeout: int = 60, interval: int = 3):
    """
    Verifies that a given URL is publicly accessible by repeatedly sending GET requests.
    """
    logger.info("Verifying public access for URL: %s", url)
    elapsed = 0
    async with httpx.AsyncClient() as client:
        while elapsed < timeout:
            try:
                response = await client.get(url, timeout=5)
                if response.is_success:
                    logger.info("URL %s is now publicly accessible.", url)
                    return True
                logger.warning(
                    "URL %s not yet public (status: %d). Retrying...",
                    url,
                    response.status_code,
                )
            except httpx.RequestError as e:
                logger.warning("Request to %s failed: %s. Retrying...", url, e)

            await asyncio.sleep(interval)
            elapsed += interval

    raise TimeoutError(f"URL {url} was not publicly accessible after {timeout} seconds.")





class MidjourneyClient:
    """
    An asynchronous client for the GoAPI V1 Midjourney service.
    """
    _BASE_URL = os.getenv("GOAPI_BASE_URL", "https://api.goapi.ai/api/v1")
    _TASK_ENDPOINT = f"{_BASE_URL}/task"

    def __init__(self, api_token: Optional[str] = None, timeout: float = 120.0):
        self._api_token = api_token or os.getenv("MIDJOURNEY_API_TOKEN")
        if not self._api_token:
            raise ValueError(
                "MIDJOURNEY_API_TOKEN not provided via parameter or environment variable"
            )
        self._timeout = httpx.Timeout(timeout)

    @property
    def _headers(self) -> Dict[str, str]:
        # Using "Authorization: Bearer ..." is the modern standard.
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            # Use explicit verbs to satisfy tests that patch/match post/get
            method_upper = method.upper()
            if method_upper == "POST":
                response = await client.post(url, headers=self._headers, **kwargs)
            elif method_upper == "GET":
                response = await client.get(url, headers=self._headers, **kwargs)
            else:
                response = await client.request(method, url, headers=self._headers, **kwargs)
            if not response.is_success:
                logger.error(
                    "GoAPI request failed. Status: %s, Response: %s",
                    response.status_code,
                    response.text,
                )
                response.raise_for_status()
            return response.json()

    async def submit_imagine(
        self,
        prompt: str,
        *,
        aspect_ratio: Optional[str],
        process_mode: Optional[str],
        oref_url: Optional[str] = None,
        oref_weight: Optional[int] = None,
        model_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit an imagine request using the V1 endpoint."""
        # Minimal normalization to satisfy tests and v7 rules
        prompt_for_payload = (prompt or "").strip()
        try:
            # If prompt starts with --oref (and possibly --ow), prefix neutral token
            if re.match(r"^\s*--oref\b", prompt_for_payload, re.IGNORECASE):
                prompt_for_payload = f"image {prompt_for_payload}"
            # If v7, strip inline --cref/--cw from prompt text (these are unsupported)
            is_v7 = (model_version == "v7") or bool(re.search(r"--v\s+7\b", prompt_for_payload, re.IGNORECASE))
            if is_v7:
                prompt_for_payload = re.sub(r"\s--cref\s+\S+", "", prompt_for_payload, flags=re.IGNORECASE)
                prompt_for_payload = re.sub(r"\s--cw\s+\S+", "", prompt_for_payload, flags=re.IGNORECASE)
                prompt_for_payload = re.sub(r"\s{2,}", " ", prompt_for_payload).strip()
        except Exception:
            prompt_for_payload = prompt

        payload: Dict[str, Any] = {
            "model": "midjourney",
            "task_type": "imagine",
            "input": {
                "prompt": prompt_for_payload,
                "process_mode": process_mode or "relax",
            },
        }
        if aspect_ratio:
            payload["input"]["aspect_ratio"] = aspect_ratio
        if oref_url:
            payload["input"]["oref"] = oref_url
        if oref_weight is not None:
            payload["input"]["ow"] = oref_weight
        # Additive: attempt to pass version explicitly if provided (cover both keys)
        if model_version:
            try:
                payload["input"]["model_version"] = model_version
                payload["input"]["version"] = model_version
            except Exception:
                pass
            
        logger.info("Submitting imagine request with payload: %s", payload)
        return await self._request("POST", self._TASK_ENDPOINT, json=payload)

    async def submit_action(
        self, origin_task_id: str, *, action: str
    ) -> Dict[str, Any]:
        """Submit an action request (upscale, variation, reroll) using the V1 endpoint."""
        # Correctly parse the action and index. E.g., "upscale2" -> "upscale", "2"
        task_type = "".join([i for i in action if not i.isdigit()]) or action
        index_str = "".join([i for i in action if i.isdigit()])

        payload: Dict[str, Any] = {
            "model": "midjourney",
            "task_type": task_type,
            "input": {"origin_task_id": origin_task_id},
        }
        
        # The API requires the index to be a STRING if it exists
        if index_str:
            payload["input"]["index"] = index_str

        # ADDITIVE NORMALIZATION: map special labels to supported unified task types
        # Do not remove existing logic; only augment payload before sending.
        try:
            if task_type in ("high_variation", "low_variation"):
                payload["task_type"] = "variation"
                payload["input"]["strength"] = "high" if task_type.startswith("high_") else "low"
        except Exception:
            pass

        logger.info("Submitting action request with payload: %s", payload)
        return await self._request("POST", self._TASK_ENDPOINT, json=payload)

    async def submit_describe(self, image_url: str) -> Dict[str, Any]:
        """Submit a describe request using the V1 endpoint."""
        payload = {
            "model": "midjourney",
            "task_type": "describe",
            "input": {
                "image_url": image_url,
            },
        }
        logger.info("Submitting describe request with payload: %s", payload)
        return await self._request("POST", self._TASK_ENDPOINT, json=payload)

    async def submit_seed(self, origin_task_id: str) -> Dict[str, Any]:
        """Submit a seed request using the V1 endpoint."""
        payload = {
            "model": "midjourney",
            "task_type": "seed",
            "input": {
                "origin_task_id": origin_task_id,
            },
        }
        logger.info("Submitting seed request with payload: %s", payload)
        return await self._request("POST", self._TASK_ENDPOINT, json=payload)

    async def submit_blend(self, image_urls: list[str], dimension: str) -> Dict[str, Any]:
        """Submit a blend request using the V1 endpoint."""
        payload = {
            "model": "midjourney",
            "task_type": "blend",
            "input": {
                "image_urls": image_urls,
                "dimension": dimension,
            },
        }
        logger.info("Submitting blend request with payload: %s", payload)
        return await self._request("POST", self._TASK_ENDPOINT, json=payload)

    async def poll_task(self, task_id: str) -> Dict[str, Any]:
        """Fetch the status of a specific task."""
        url = f"{self._TASK_ENDPOINT}/{task_id}"
        return await self._request("GET", url)

    async def download_image(self, url: str, output_path: str) -> None:
        """Utility to download an image asynchronously."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)

async def poll_until_complete(client: MidjourneyClient, task_id: str, interval: int = 5, max_wait: int = 900) -> Dict[str, Any]:
    """Polls a task until it is completed, failed, or timed out."""
    elapsed = 0
    while elapsed < max_wait:
        try:
            result = await client.poll_task(task_id)
            task_data = result.get("data", result)

            status = task_data.get("status")
            if status in {"completed", "finished"}:
                logger.info("Task %s finished successfully.", task_id)
                return task_data
            if status in {"failure", "failed", "error"}:
                logger.error("Task %s failed with data: %s", task_id, task_data)
                raise MidjourneyError(f"Task failed: {task_data}")
            
            logger.debug("Task %s status: %s, progress: %s%%", task_id, status, task_data.get("output", {}).get("progress", 0))
            await asyncio.sleep(interval)
            elapsed += interval

        except httpx.HTTPStatusError as e:
            # It can take a moment for a new task to be found by the API.
            # We will retry on 404s for a short grace period.
            if e.response.status_code == 404 and elapsed < 30:
                logger.warning("Task %s not found yet, retrying...", task_id)
                await asyncio.sleep(interval)
                elapsed += interval
                continue
            raise  # Re-raise other HTTP errors immediately

    raise TimeoutError(f"Task {task_id} did not complete after {max_wait}s")


async def split_grid_and_upload(task_id: str, image_path: Path, bucket_name: str) -> List[str]:
    """
    Splits a 2x2 grid image into four quadrants and uploads them to GCS **in memory**.
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image grid not found at {image_path}")

    loop = asyncio.get_running_loop()
    
    with Image.open(image_path) as image:
        # The grid is always 2x2, so we just need to find the midpoint
        # regardless of the original aspect ratio.
        width, height = image.size
        mid_x, mid_y = width // 2, height // 2

        # Define the four quadrants based on the calculated midpoints
        quadrants = [
            (0, 0, mid_x, mid_y),       # Top-left
            (mid_x, 0, width, mid_y),    # Top-right
            (0, mid_y, mid_x, height),   # Bottom-left
            (mid_x, mid_y, width, height) # Bottom-right
        ]
        
        upload_tasks = []
        for i, box in enumerate(quadrants):
            quadrant = image.crop(box)
            byte_arr = BytesIO()
            quadrant.save(byte_arr, format='PNG')
            image_bytes = byte_arr.getvalue()
            
            object_name = f"split/{task_id}_quadrant_{i+1}.png"
            
            task = loop.run_in_executor(
                None,
                upload_to_gcs_and_get_public_url,
                image_bytes,
                object_name
            )
            upload_tasks.append(task)
        
        gcs_urls = await asyncio.gather(*upload_tasks)

    logger.info("Split grid for task %s into 4 images.", task_id)
    return gcs_urls

