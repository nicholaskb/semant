import os
import sys
import json
import asyncio
import argparse
from typing import Any, Dict


async def poll_until_complete(get_task_tool, task_id: str, interval: float = 5.0, timeout: int = 900) -> Dict[str, Any]:
    elapsed = 0.0
    while elapsed < timeout:
        res = await get_task_tool.run(task_id=task_id)
        data = res.get("data", res)
        status = (data or {}).get("status")
        if status in {"completed", "finished"}:
            return data
        if status in {"failure", "failed", "error"}:
            raise RuntimeError(json.dumps(data))
        await asyncio.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"Task {task_id} did not complete in {timeout}s")


async def main():
    parser = argparse.ArgumentParser(description="Run a Midjourney action (e.g., upscale2) and mirror result to GCS")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--action", required=True, help="e.g., upscale1..4, variation2, reroll")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    if not os.getenv("MIDJOURNEY_API_TOKEN"):
        print("ERROR: MIDJOURNEY_API_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    from semant.agent_tools.midjourney import REGISTRY

    action_tool = REGISTRY["mj.action"]()
    res = await action_tool.run(origin_task_id=args.task_id, action=args.action)
    print("Action response:", json.dumps(res))

    # Extract new task id (some APIs create a new task for action)
    data = res.get("data", res)
    new_task_id = (data or {}).get("task_id") or (data or {}).get("id") or args.task_id

    get_task = REGISTRY["mj.get_task"]()
    final = await poll_until_complete(get_task, new_task_id, interval=args.interval, timeout=args.timeout)
    print("Final action task:", json.dumps(final))

    # Grab image url
    output = (final or {}).get("output", {})
    image_url = output.get("image_url") or output.get("url")
    if image_url:
        mirror = REGISTRY["mj.gcs_mirror"]()
        mirrored = await mirror.run(source_url=image_url, task_id=new_task_id, filename=f"{args.action}.png")
        print("Mirrored to GCS:", json.dumps(mirrored))


if __name__ == "__main__":
    asyncio.run(main())


