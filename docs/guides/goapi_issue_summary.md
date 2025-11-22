# GoAPI Midjourney PPU - `action` Endpoint Failure Analysis

## 1. Problem Statement

We are developing a Python CLI toolkit to interact with the GoAPI Midjourney service on a **Pay-Per-Use (PPU)** plan.

While we can successfully submit an initial `imagine` task and retrieve the results, **every attempt to perform a follow-up action (such as `upscale`, `variation`, or `reroll`) has failed with `404 Not Found` or `500 Internal Server Error` responses.**

We have tried numerous permutations of GoAPI's V1 and V2 documentation for action endpoints, none of which have worked. The core of the problem is identifying the correct HTTP request structure (method, URL, and payload) for these follow-up actions on a PPU account.

## 2. What Works: Submitting an `imagine` Task

The initial image generation works reliably. The toolkit sends the following request:

*   **Method**: `POST`
*   **Endpoint**: `https://api.goapi.ai/api/v1/midjourney/task`
*   **Headers**:
    *   `Content-Type: application/json`
    *   `X-API-KEY: <your_api_key>`
*   **Body**:
    ```json
    {
      "model": "midjourney",
      "task_type": "imagine",
      "input": {
        "prompt": "your prompt here",
        "aspect_ratio": "1:1"
      }
    }
    ```

This correctly queues a task. We can then poll `GET /api/v1/midjourney/task/<task_id>` to get the final result, which includes an `actions` array.

## 3. What Fails: Performing an Action (e.g., `upscale1`)

Using the `task_id` from a completed `imagine` task, we have tried various documented and logical permutations to trigger an `upscale1` action. All have failed.

### Attempted Requests (All Failed)

| Attempt                                 | Method | URL                                       | Payload                                                  | Result             |
| --------------------------------------- | ------ | ----------------------------------------- | -------------------------------------------------------- | ------------------ |
| **V2 Doc, Action Endpoint**             | `POST` | `/api/v2/midjourney/task/upscale`         | `{"task_id": "...", "index": 1}`                         | `404 Not Found`    |
| **V1 Doc, BYOA-style Button**           | `POST` | `/api/v1/task/button`                     | `{"origin_task_id": "...", "custom_id": "..."}`          | `404 Not Found`    |
| **V1 Doc, PPU-style Button**            | `POST` | `/api/v1/midjourney/task/.../button`      | `{"button": "upscale1"}`                                 | `404 Not Found`    |
| **V1 Doc, PPU-style Button in URL**     | `POST` | `/api/v1/midjourney/task/.../button/upscale1` | `{}`                                                     | `404 Not Found`    |
| **Logical Guess: V1 `task` endpoint**   | `POST` | `/api/v1/midjourney/task`                 | `{"task_id": "...", "task_type": "upscale", "index": 1}` | `500 Server Error` |

This demonstrates a fundamental misunderstanding of the required API call structure, which the documentation has not clarified.

## 4. Supporting Evidence: `metadata.json`

This is the full, successful JSON response from an `imagine` task. Note the simple string array in `output.actions`, which is the only information provided for triggering follow-up tasks.

```json
{
  "task_id": "ba8d80d2-47ba-4d96-a710-ecb0bae7bc5f",
  "model": "midjourney",
  "task_type": "imagine",
  "status": "completed",
  "config": { "service_mode": "public", "webhook_config": { "endpoint": "", "secret": "" } },
  "input": { "aspect_ratio": "1:1", "prompt": "test prompt" },
  "output": {
    "image_url": "https://img.theapi.app/mj/ba8d80d2-47ba-4d96-a710-ecb0bae7bc5f.png",
    "image_urls": [
      "https://cdn.midjourney.com/3818e0e2-cc8c-4f28-acbf-9274cd8e2e27/0_0.png",
      "https://cdn.midjourney.com/3818e0e2-cc8c-4f28-acbf-9274cd8e2e27/0_1.png",
      "https://cdn.midjourney.com/3818e0e2-cc8c-4f28-acbf-9274cd8e2e27/0_2.png",
      "https://cdn.midjourney.com/3818e0e2-cc8c-4f28-acbf-9274cd8e2e27/0_3.png"
    ],
    "temporary_image_urls": null,
    "discord_image_url": "",
    "actions": [
      "reroll", "upscale1", "upscale2", "upscale3", "upscale4",
      "variation1", "variation2", "variation3", "variation4"
    ],
    "progress": 100,
    "intermediate_image_urls": null
  },
  "meta": { "created_at": "2025-07-21T02:55:32Z", "started_at": "2025-07-21T02:55:41Z", "ended_at": "2025-07-21T02:56:13Z", "usage": { "type": "mj", "frozen": 14, "consume": 8 }, "is_using_private_pool": false, "model_version": "unknown", "process_mode": "relax", "failover_triggered": false },
  "detail": null,
  "logs": [],
  "error": { "code": 0, "raw_message": "", "message": "", "detail": null }
}
```

## 5. Current Code

Here is the complete code for the toolkit in its last working state (where `imagine` succeeds and `action` is disabled).

### File: `midjourney_integration/goapi_generate.py`

```python
"""
GoAPI Midjourney - Pay-Per-Use helper script.
This module provides core functions to interact with the GoAPI V1 endpoints.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()
_API_KEY = os.getenv("MIDJOURNEY_API_TOKEN")
if not _API_KEY:
    print("[goapi-helper] ERROR: MIDJOURNEY_API_TOKEN not set", file=sys.stderr)
    sys.exit(1)

# V1 endpoint for imagine and polling
_BASE_URL = os.getenv("GOAPI_BASE_URL", "https://api.goapi.ai/api/v1")
_TASK_ENDPOINT = f"{_BASE_URL}/midjourney/task"
_HEADERS = {"X-API-KEY": _API_KEY, "Content-Type": "application/json"}


def _download_image(url: str, output_dir: str, filename: str | None = None) -> str:
    """Utility to download an image from a URL."""
    os.makedirs(output_dir, exist_ok=True)
    if not filename:
        filename = url.split("/")[-1].split("?")[0]
    path = os.path.join(output_dir, filename)
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)
    return path

# ---------------------------------------------------------------------------
# API helpers (V1)
# ---------------------------------------------------------------------------

def submit_imagine(prompt: str, *, aspect_ratio: str, process_mode: str | None) -> Dict[str, Any]:
    """Submit an imagine request using the V1 endpoint."""
    url = _TASK_ENDPOINT
    payload: Dict[str, Any] = {
        "model": "midjourney",
        "task_type": "imagine",
        "input": {"prompt": prompt, "aspect_ratio": aspect_ratio},
    }
    if process_mode:
        payload["input"]["process_mode"] = process_mode

    r = requests.post(url, headers=_HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def poll_task(task_id: str, *, interval: int = 3, max_wait: int = 600) -> Dict[str, Any]:
    """Poll /task/{id} until finished or timeout. Returns final JSON."""
    url = f"{_TASK_ENDPOINT}/{task_id}"
    elapsed = 0
    while elapsed < max_wait:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        # V1 responses are wrapped in a 'data' object
        task_data = data.get("data", {})
        if task_data.get("status") in {"finished", "completed"}:
            return task_data
        if task_data.get("status") in {"failure", "failed", "error"}:
            raise RuntimeError(f"Task failed: {task_data}")
        time.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"Task {task_id} not finished after {max_wait}s")
```

### File: `midjourney_integration/cli.py`

```python
"""
Midjourney Toolkit – unified CLI around GoAPI.
"""
from __future__ import annotations

import argparse
import json
import os
import pprint
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

from . import goapi_generate as client

# Mapping of action types to GoAPI PPU endpoints
ACTION_ENDPOINTS: Dict[str, str] = {
    "upscale": "upscale",
    "variation": "variation",
    "reroll": "reroll",
}

_JOBS_DIR = Path(__file__).resolve().parent / "jobs"
_JOBS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _task_path(task_id: str) -> Path:
    return _JOBS_DIR / task_id


def _meta_file(task_id: str) -> Path:
    return _task_path(task_id) / "metadata.json"


def _save_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


def _load_metadata(task_id: str) -> Dict[str, Any]:
    path = _meta_file(task_id)
    if not path.exists():
        raise FileNotFoundError(f"No metadata for task {task_id}")
    return json.loads(path.read_text())

# ---------------------------------------------------------------------------
# Command Implementations
# ---------------------------------------------------------------------------

def _store_result(task_id: str, payload: Dict[str, Any]) -> None:
    payload = payload.get("data", payload)
    dir_path = _task_path(task_id)
    dir_path.mkdir(parents=True, exist_ok=True)
    img_url = (
        payload.get("output", {}).get("discord_image_url")
        or payload.get("output", {}).get("image_url")
    )
    if img_url:
        img_path = dir_path / "original.png"
        if not img_path.exists():
            client._download_image(img_url, str(dir_path), "original.png")
    _save_json_atomic(_meta_file(task_id), payload)
    print(f"[toolkit] Stored task {task_id} -> {dir_path}")

def _poll_with_progress(task_id: str, *, interval: int, max_wait: int) -> Dict[str, Any]:
    elapsed = 0
    while True:
        data = client.poll_task(task_id, interval=1, max_wait=max_wait - elapsed)
        status = data.get("status", "?")
        prog = data.get("output", {}).get("progress", 0)
        print(f"[{task_id[:8]}] {status} {prog}%", end="\r", flush=True)
        if status in {"finished", "completed"}:
            print()
            return data
        time.sleep(interval)
        elapsed += interval
        if elapsed > max_wait:
            print()
            raise TimeoutError("Polling timed out")

def cmd_imagine(args: argparse.Namespace):
    resp = client.submit_imagine(
        args.prompt, aspect_ratio=args.aspect_ratio, process_mode=args.mode
    )
    task_id = resp.get("data", resp).get("task_id")
    if not task_id:
        raise RuntimeError(f"Could not get task_id from response: {resp}")

    print(f"[toolkit] Task submitted with ID: {task_id}")
    _store_result(task_id, resp)

    if args.background:
        _spawn_background_follower(
            task_id, interval=args.interval, max_wait=args.max_wait
        )
        print(f"[toolkit] Background follower spawned for task {task_id}")
    elif not args.nowait:
        print("[toolkit] Polling for completion…")
        payload = _poll_with_progress(
            task_id, interval=args.interval, max_wait=args.max_wait
        )
        _store_result(task_id, payload)

def cmd_action(args: argparse.Namespace) -> None:
    print("[toolkit] Action command is currently disabled pending API clarification.")
    pass

# ... Other helper implementations (follow, list, etc.) are omitted for brevity ...

# ---------------------------------------------------------------------------
# Main Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser("Midjourney toolkit")
    # ... (full argparse setup here) ...

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[toolkit] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
```

## 6. Question for the Expert

Given the successful `imagine` call and the resulting `metadata.json`, what is the correct and complete HTTP request (Method, URL, Headers, and Body) required to perform an **`upscale1`** action for a GoAPI Pay-Per-Use account? 