import os
import sys
import json
import asyncio
import argparse
from typing import Any, Dict


async def poll_until_complete(get_task_tool, task_id: str, interval: float = 5.0, timeout: int = 900) -> Dict[str, Any]:
    elapsed = 0.0
    while elapsed < timeout:
        try:
            res = await get_task_tool.run(task_id=task_id)
            data = res.get("data", res)
            status = (data or {}).get("status")
            if status in {"completed", "finished"}:
                return data
            if status in {"failure", "failed", "error"}:
                raise RuntimeError(f"Task failed: {json.dumps(data)}")
        except Exception as e:
            # Transient errors will be handled by client backoff; keep polling unless timeout
            print(f"[poll] warning: {e}")
        await asyncio.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")


async def main():
    parser = argparse.ArgumentParser(description="Live Midjourney GoAPI demo using agent tools")
    parser.add_argument("--prompt", required=True, help="Prompt text for imagine")
    parser.add_argument("--version", choices=["v6", "v7"], default="v7")
    parser.add_argument("--aspect-ratio", dest="aspect_ratio", default=None)
    parser.add_argument("--process-mode", dest="process_mode", default=None)
    parser.add_argument("--oref", default=None, help="V7-only reference image URL")
    parser.add_argument("--ow", type=int, default=None, help="V7-only reference weight")
    parser.add_argument("--cref", default=None, help="V6-only reference image URL")
    parser.add_argument("--cw", type=int, default=None, help="V6-only reference weight")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval seconds")
    parser.add_argument("--timeout", type=int, default=900, help="Polling timeout seconds")
    args = parser.parse_args()

    token = os.getenv("MIDJOURNEY_API_TOKEN")
    if not token:
        print("ERROR: MIDJOURNEY_API_TOKEN is not set in environment", file=sys.stderr)
        sys.exit(1)

    from semant.agent_tools.midjourney import REGISTRY

    imagine = REGISTRY["mj.imagine"]()
    res = await imagine.run(
        prompt=args.prompt,
        model_version=args.version,
        aspect_ratio=args.aspect_ratio,
        process_mode=args.process_mode,
        oref=args.oref,
        ow=args.ow,
        cref=args.cref,
        cw=args.cw,
    )
    print("Imagine response:", json.dumps(res))

    # Extract task id
    data = res.get("data", res)
    task_id = (data or {}).get("task_id") or (data or {}).get("id")
    if not task_id:
        print("ERROR: could not determine task_id from response", file=sys.stderr)
        sys.exit(2)

    get_task = REGISTRY["mj.get_task"]()
    final = await poll_until_complete(get_task, task_id, interval=args.interval, timeout=args.timeout)
    print("Final task:", json.dumps(final))
    # Print any known image URL fields
    output = (final or {}).get("output", {})
    image_url = None
    for key in ("image_url", "image", "url"):
        if key in output and output[key]:
            image_url = output[key]
            print(f"Output {key}: {image_url}")
            break

    # Optional: mirror to GCS if available
    if image_url:
        try:
            mirror = REGISTRY["mj.gcs_mirror"]()
            mirrored = await mirror.run(source_url=image_url, task_id=task_id, filename="image.png")
            print("Mirrored to GCS:", json.dumps(mirrored))
        except Exception as e:
            print(f"GCS mirror skipped/failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())


