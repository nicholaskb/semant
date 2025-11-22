"""GoAPI Midjourney – Pay-Per-Use example.

Usage:
    python examples/goapi_midjourney_imagine.py "your prompt here" [--mode fast] [--aspect_ratio 1:1]

Environment variables (read from .env if present):
    GOAPI_API_KEY       Required – your GoAPI Midjourney key (PPU plan)
    GOAPI_BASE_URL      Optional – defaults to "https://api.goapi.ai/api/v1"

The script submits an imagine task, polls `/task/{id}` until status == "finished",
then prints the final JSON (including `image_url`).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------
load_dotenv()
_API_KEY = os.getenv("GOAPI_API_KEY")
if not _API_KEY:
    print("[goapi-demo] ERROR: GOAPI_API_KEY not set (check your .env)", file=sys.stderr)
    sys.exit(1)

_BASE_URL = os.getenv("GOAPI_BASE_URL", "https://api.goapi.ai/api/v1")
_TASK_ENDPOINT = f"{_BASE_URL}/task"
_HEADERS = {"X-API-KEY": _API_KEY, "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def submit_imagine(prompt: str, *, aspect_ratio: str, process_mode: str | None) -> str:
    """Submit an imagine request. Returns the new task_id (str)."""
    body: Dict[str, Any] = {
        "model": "midjourney",
        "task_type": "imagine",
        "input": {"prompt": prompt, "aspect_ratio": aspect_ratio},
    }
    if process_mode:
        body["input"]["process_mode"] = process_mode

    r = requests.post(_TASK_ENDPOINT, headers=_HEADERS, json=body, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") == "finished":  # rare fast-path
        return data
    task_id = data.get("task_id") or data.get("result")
    if not task_id:
        raise RuntimeError(f"Unexpected response: {data}")
    return task_id  # type: ignore[return-value]


def poll_task(task_id: str, *, interval: int = 3, max_wait: int = 300) -> Dict[str, Any]:
    """Poll /task/{id} until finished or timeout. Returns final JSON."""
    url = f"{_TASK_ENDPOINT}/{task_id}"
    elapsed = 0
    while elapsed < max_wait:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "finished":
            return data  # contains image_url
        time.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"Task {task_id} not finished after {max_wait}s")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Midjourney images via GoAPI (PPU)")
    parser.add_argument("prompt", help="Text prompt to generate")
    parser.add_argument("--aspect_ratio", default="1:1", help="Aspect ratio, e.g. 16:9")
    parser.add_argument("--mode", choices=["relax", "fast", "turbo"], help="Process mode")
    args = parser.parse_args()

    print("[goapi-demo] Submitting imagine task…")
    task_id_or_data = submit_imagine(args.prompt, aspect_ratio=args.aspect_ratio, process_mode=args.mode)

    if isinstance(task_id_or_data, dict):
        # Already finished
        print(json.dumps(task_id_or_data, indent=2))
        return

    task_id = task_id_or_data
    print(f"[goapi-demo] Task queued: {task_id}. Polling for completion…")
    final = poll_task(task_id)

    print(json.dumps(final, indent=2))
    print("[goapi-demo] Image URL:", final.get("image_url"))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"[goapi-demo] ERROR: {exc}", file=sys.stderr)
        sys.exit(2) 