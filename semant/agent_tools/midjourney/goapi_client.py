"""
Asynchronous GoAPI client for Midjourney, scoped for agent tools.

This client is independent of the legacy `midjourney_integration/` package.
It provides:
 - Auth via MIDJOURNEY_API_TOKEN (no hard-coded secrets)
 - Parameter validation with model-version awareness
 - Resilient HTTP requests with exponential backoff and jitter on 429/5xx
 - Clear, user-friendly error messages

Endpoints (unified):
 - POST {BASE}/task            → create tasks (imagine, action, describe, blend, inpaint, outpaint, pan, zoom, seed)
 - GET  {BASE}/task/{task_id}  → get task status

Notes:
 - Cancel endpoint variants differ across providers; we expose a generic `cancel_task` stub
   that can be wired once the canonical path is confirmed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


logger = logging.getLogger(__name__)


DEFAULT_BASE_URL = os.getenv("GOAPI_BASE_URL", "https://api.goapi.ai/api/v1")


class GoAPIClientError(RuntimeError):
    """Raised for GoAPI client failures after retries or validation errors."""


@dataclass
class RetryPolicy:
    max_retries: int = 5
    initial_delay_seconds: float = 0.8
    max_delay_seconds: float = 8.0
    backoff_factor: float = 2.0
    jitter_fraction: float = 0.25  # add ±25% jitter


def _with_jitter(seconds: float, jitter_fraction: float) -> float:
    if seconds <= 0 or jitter_fraction <= 0:
        return max(seconds, 0)
    delta = seconds * jitter_fraction
    return max(0.0, seconds + random.uniform(-delta, delta))


class GoAPIClient:
    """Async GoAPI client tailored for agent tools.

    This class intentionally does not depend on project-specific settings modules.
    """

    def __init__(
        self,
        *,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        request_timeout_seconds: float = 120.0,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        self._api_token: str | None = api_token or os.getenv("MIDJOURNEY_API_TOKEN")
        if not self._api_token:
            raise GoAPIClientError(
                "MIDJOURNEY_API_TOKEN not provided (set env var or pass api_token)"
            )

        self._base_url: str = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._task_endpoint: str = f"{self._base_url}/task"
        self._timeout = httpx.Timeout(request_timeout_seconds)
        self._retry_policy = retry_policy or RetryPolicy()

    # ---------------------------
    # Public high-level API
    # ---------------------------
    async def imagine(
        self,
        *,
        prompt: str,
        model_version: Optional[str] = None,  # e.g., "v6" or "v7"
        aspect_ratio: Optional[str] = None,
        process_mode: Optional[str] = None,
        # Reference controls
        cref: Optional[str] = None,
        cw: Optional[int] = None,
        oref: Optional[str] = None,
        ow: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create an imagine task with strict parameter validation.

        Version-aware rules:
        - V6-only: `cref`, `cw`
        - V7-only: `oref`, `ow`
        """
        self._validate_model_version(model_version)
        self._validate_reference_params(model_version, cref=cref, cw=cw, oref=oref, ow=ow)

        input_payload: Dict[str, Any] = {
            "prompt": (prompt or "").strip(),
        }
        if aspect_ratio:
            input_payload["aspect_ratio"] = aspect_ratio
        if process_mode:
            input_payload["process_mode"] = process_mode
        if model_version:
            input_payload["model_version"] = model_version
            input_payload["version"] = model_version
        if cref is not None:
            input_payload["cref"] = cref
        if cw is not None:
            input_payload["cw"] = cw
        if oref is not None:
            input_payload["oref"] = oref
        if ow is not None:
            input_payload["ow"] = ow
        if extra:
            input_payload.update(extra)

        payload = {
            "model": "midjourney",
            "task_type": "imagine",
            "input": input_payload,
        }
        return await self._post_task(payload)

    async def action(self, *, origin_task_id: str, action: str) -> Dict[str, Any]:
        """Submit an action (upscale, variation, reroll)."""
        task_type, index = self._parse_action(action)

        payload = {
            "model": "midjourney",
            "task_type": task_type,
            "input": {"origin_task_id": origin_task_id},
        }
        if index is not None:
            payload["input"]["index"] = index

        # Normalize special variations
        if task_type in {"high_variation", "low_variation"}:
            payload["task_type"] = "variation"
            payload["input"]["strength"] = "high" if task_type.startswith("high_") else "low"

        return await self._post_task(payload)

    async def describe(self, *, image_url: str) -> Dict[str, Any]:
        payload = {
            "model": "midjourney",
            "task_type": "describe",
            "input": {"image_url": image_url},
        }
        return await self._post_task(payload)

    async def seed(self, *, origin_task_id: str) -> Dict[str, Any]:
        payload = {
            "model": "midjourney",
            "task_type": "seed",
            "input": {"origin_task_id": origin_task_id},
        }
        return await self._post_task(payload)

    async def blend(self, *, image_urls: list[str], dimension: str) -> Dict[str, Any]:
        payload = {
            "model": "midjourney",
            "task_type": "blend",
            "input": {"image_urls": image_urls, "dimension": dimension},
        }
        return await self._post_task(payload)

    async def inpaint(
        self,
        *,
        image_url: str,
        mask_url: str,
        prompt: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._validate_inpaint_args(image_url=image_url, mask_url=mask_url)
        input_payload: Dict[str, Any] = {
            "image_url": image_url,
            "mask_url": mask_url,
        }
        if prompt:
            input_payload["prompt"] = prompt
        if extra:
            input_payload.update(extra)

        payload = {
            "model": "midjourney",
            "task_type": "inpaint",
            "input": input_payload,
        }
        return await self._post_task(payload)

    async def outpaint(
        self,
        *,
        image_url: str,
        prompt: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._validate_outpaint_args(image_url=image_url)
        input_payload: Dict[str, Any] = {
            "image_url": image_url,
        }
        if prompt:
            input_payload["prompt"] = prompt
        if extra:
            input_payload.update(extra)

        payload = {
            "model": "midjourney",
            "task_type": "outpaint",
            "input": input_payload,
        }
        return await self._post_task(payload)

    async def pan(self, *, origin_task_id: str, direction: str) -> Dict[str, Any]:
        self._validate_pan_args(direction=direction)
        payload = {
            "model": "midjourney",
            "task_type": "pan",
            "input": {"origin_task_id": origin_task_id, "direction": direction},
        }
        return await self._post_task(payload)

    async def zoom(self, *, origin_task_id: str, factor: float | int) -> Dict[str, Any]:
        self._validate_zoom_args(factor=factor)
        payload = {
            "model": "midjourney",
            "task_type": "zoom",
            "input": {"origin_task_id": origin_task_id, "factor": factor},
        }
        return await self._post_task(payload)

    # ---------------------------
    # Argument validation helpers
    # ---------------------------
    @staticmethod
    def _is_http_url(value: Optional[str]) -> bool:
        return bool(value) and (str(value).startswith("http://") or str(value).startswith("https://"))

    def _validate_inpaint_args(self, *, image_url: str, mask_url: str) -> None:
        if not self._is_http_url(image_url):
            raise GoAPIClientError("inpaint.image_url must be an http(s) URL")
        if not self._is_http_url(mask_url):
            raise GoAPIClientError("inpaint.mask_url must be an http(s) URL")

    def _validate_outpaint_args(self, *, image_url: str) -> None:
        if not self._is_http_url(image_url):
            raise GoAPIClientError("outpaint.image_url must be an http(s) URL")

    def _validate_pan_args(self, *, direction: str) -> None:
        valid = {"up", "down", "left", "right"}
        if str(direction).lower() not in valid:
            raise GoAPIClientError(f"pan.direction must be one of {sorted(valid)}")

    def _validate_zoom_args(self, *, factor: float | int) -> None:
        try:
            f = float(factor)
        except Exception:
            raise GoAPIClientError("zoom.factor must be a number")
        if f <= 0:
            raise GoAPIClientError("zoom.factor must be greater than 0")

    async def get_task(self, *, task_id: str) -> Dict[str, Any]:
        url = f"{self._task_endpoint}/{task_id}"
        return await self._request("GET", url)

    async def cancel_task(self, *, task_id: str) -> Dict[str, Any]:
        """Cancel a task if the API supports it.

        Note: The canonical cancel path can vary. This method is a placeholder
        that should be updated when the official endpoint is confirmed.
        """
        payload = {
            "model": "midjourney",
            "task_type": "cancel",
            "input": {"task_id": task_id},
        }
        return await self._post_task(payload)

    # ---------------------------
    # Internal helpers
    # ---------------------------
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

    async def _post_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Log lightweight sanitized payload (no secrets)
        try:
            logger.info("POST /task payload keys: %s", list(payload.keys()))
        except Exception:
            pass
        return await self._request("POST", self._task_endpoint, json=payload)

    async def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        policy = self._retry_policy
        delay = policy.initial_delay_seconds
        last_exc: Exception | None = None

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(policy.max_retries + 1):
                try:
                    if method.upper() == "POST":
                        resp = await client.post(url, headers=self._headers(), **kwargs)
                    elif method.upper() == "GET":
                        resp = await client.get(url, headers=self._headers(), **kwargs)
                    else:
                        resp = await client.request(method, url, headers=self._headers(), **kwargs)

                    if resp.status_code == 429 or 500 <= resp.status_code < 600:
                        # Retriable
                        if attempt < policy.max_retries:
                            sleep_for = _with_jitter(min(delay, policy.max_delay_seconds), policy.jitter_fraction)
                            logger.warning(
                                "GoAPI %s %s -> %s; retrying in %.2fs (attempt %d/%d)",
                                method.upper(), url, resp.status_code, sleep_for, attempt + 1, policy.max_retries,
                            )
                            await asyncio.sleep(sleep_for)
                            delay *= policy.backoff_factor
                            continue
                        resp.raise_for_status()

                    # Non-retriable 4xx (other than 429)
                    resp.raise_for_status()
                    try:
                        return resp.json()
                    except json.JSONDecodeError:
                        # Some endpoints return empty bodies on success
                        return {"status": "ok", "raw": resp.text}

                except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                    last_exc = exc
                    # If not retriable or retries exhausted
                    if isinstance(exc, httpx.HTTPStatusError):
                        status = exc.response.status_code
                        if status != 429 and not (500 <= status < 600):
                            break
                    if attempt >= policy.max_retries:
                        break
                    sleep_for = _with_jitter(min(delay, policy.max_delay_seconds), policy.jitter_fraction)
                    logger.warning(
                        "GoAPI request error (%s). Retrying in %.2fs (attempt %d/%d)",
                        type(exc).__name__, sleep_for, attempt + 1, policy.max_retries,
                    )
                    await asyncio.sleep(sleep_for)
                    delay *= policy.backoff_factor

        message = "GoAPI request failed"
        if last_exc:
            if isinstance(last_exc, httpx.HTTPStatusError):
                message = f"GoAPI request failed (status={last_exc.response.status_code})"
            else:
                message = f"GoAPI request error: {type(last_exc).__name__}"
        raise GoAPIClientError(message)

    # ---------------------------
    # Validation helpers
    # ---------------------------
    @staticmethod
    def _validate_model_version(model_version: Optional[str]) -> None:
        if model_version is None:
            return
        normalized = model_version.strip().lower()
        if normalized not in {"v6", "v7"}:
            raise GoAPIClientError(
                f"Unsupported model_version '{model_version}'. Supported: v6, v7"
            )

    @staticmethod
    def _validate_reference_params(
        model_version: Optional[str], *, cref: Optional[str], cw: Optional[int], oref: Optional[str], ow: Optional[int]
    ) -> None:
        if model_version is None:
            # If version unspecified, allow either set but not mixed to avoid ambiguity
            if (cref is not None or cw is not None) and (oref is not None or ow is not None):
                raise GoAPIClientError(
                    "Both V6 (cref/cw) and V7 (oref/ow) parameters supplied without model_version."
                )
            return

        is_v7 = model_version.strip().lower() == "v7"
        if is_v7:
            if cref is not None or cw is not None:
                raise GoAPIClientError("--cref/--cw are not supported on v7. Use --oref/--ow.")
        else:  # v6
            if oref is not None or ow is not None:
                raise GoAPIClientError("--oref/--ow are not supported on v6. Use --cref/--cw.")

    @staticmethod
    def _parse_action(action: str) -> tuple[str, Optional[str]]:
        action = (action or "").strip()
        if not action:
            raise GoAPIClientError("Action must be a non-empty string, e.g., 'upscale2' or 'reroll'.")
        # Split letters vs digits, e.g., "upscale2" -> ("upscale", "2")
        letters = "".join(ch for ch in action if not ch.isdigit())
        digits = "".join(ch for ch in action if ch.isdigit())
        return letters or action, digits or None


