"""
Midjourney Toolkit – unified CLI around GoAPI.

This CLI provides direct command-line access to the Midjourney service.
The web server backend uses the `client.py` module directly and does not
depend on this CLI script.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# The client will use the centralized settings automatically.
# No need to load .env here anymore.
from . import client as unified_client


# [REFACTOR] This is now the single source of truth for the jobs directory
_JOBS_DIR = Path(__file__).resolve().parent / "jobs"
_JOBS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Command Implementations
# ---------------------------------------------------------------------------

def cmd_imagine(args: argparse.Namespace):
    """
    Handler for the 'imagine' command. This is a CLI-only function.
    It runs in the foreground and blocks until the task is complete.
    """
    # [REFACTOR] Use the new client directly
    # Note: The CLI is synchronous, so we create a new event loop to run the async funcs.
    import asyncio

    mj_client = unified_client.MidjourneyClient()

    final_prompt = args.prompt
    if args.image_path:
        print(f"[CLI] Uploading {args.image_path} to GCS...")
        image_path = Path(args.image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found at: {args.image_path}")
        
        public_url = unified_client.upload_to_gcs_and_get_public_url(
            image_path, image_path.name
        )
        final_prompt = f"{public_url} {args.prompt}"

    print(f"[CLI] Submitting task for prompt: '{final_prompt}'")

    async def _run():
        response = await mj_client.submit_imagine(
            prompt=final_prompt,
            aspect_ratio=args.aspect_ratio,
            process_mode=args.mode,
            model_version=args.version,
        )
        task_id = response.get("data", response).get("task_id")
        if not task_id:
            raise unified_client.MidjourneyError(f"Could not get task_id from response: {response}")
            
        print(f"[CLI] Task submitted with ID: {task_id}")
        
        if not args.nowait:
            print("[CLI] Polling for completion...")
            final_payload = await unified_client.poll_until_complete(mj_client, task_id)
            print("[CLI] Task completed!")
            print(json.dumps(final_payload, indent=2))

    asyncio.run(_run())


def cmd_action(args: argparse.Namespace) -> None:
    """
    Handler for the 'action' command. Runs in the foreground.
    """
    import asyncio
    
    mj_client = unified_client.MidjourneyClient()
    print(f"[CLI] Submitting action '{args.action}' for task {args.origin_task_id}...")
    
    async def _run():
        response = await mj_client.submit_action(
            origin_task_id=args.origin_task_id,
            action=args.action
        )
        new_task_id = response.get("data", response).get("task_id")
        if not new_task_id:
            raise unified_client.MidjourneyError(f"Could not get new task_id from response: {response}")

        print(f"[CLI] Action queued as new task: {new_task_id}")
        
        if not args.nowait:
            print("[CLI] Polling for completion...")
            final_payload = await unified_client.poll_until_complete(mj_client, new_task_id)
            print("[CLI] Task completed!")
            print(json.dumps(final_payload, indent=2))

    asyncio.run(_run())


def cmd_list(_args: argparse.Namespace) -> None:
    """Lists all locally stored jobs."""
    rows: List[str] = []
    for task_dir in sorted(_JOBS_DIR.iterdir(), key=os.path.getmtime, reverse=True):
        if not task_dir.is_dir():
            continue
        meta_file = task_dir / "metadata.json"
        if not meta_file.exists():
            continue
        data = json.loads(meta_file.read_text())
        status = data.get("status", "unknown")
        prompt = data.get("input", {}).get("prompt", "-")
        rows.append(f"{task_dir.name[:8]}…  {status:<10}  {prompt[:60]}")
        
    if not rows:
        print("No jobs stored yet.")
    else:
        print("ID        Status      Prompt")
        print("-" * 70)
        for r in rows:
            print(r)

# ---------------------------------------------------------------------------
# Main Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser("Midjourney toolkit CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_im = sub.add_parser("imagine", help="Submit a new prompt and wait for result")
    p_im.add_argument("prompt")
    p_im.add_argument(
        "--image-path",
        type=str,
        default=None,
        help="Path to a local image to upload and include in the prompt.",
    )
    p_im.add_argument("--aspect_ratio", default="1:1")
    p_im.add_argument("--mode", choices=["relax", "fast", "turbo"], default="relax")
    p_im.add_argument("--version", help="Model version (v6, v7, niji 6, nano-banana)", default=None)
    p_im.add_argument("--nowait", action="store_true", help="Return immediately after submission")
    p_im.set_defaults(func=cmd_imagine)

    p_act = sub.add_parser("action", help="Trigger a button action on a completed task")
    p_act.add_argument("action", help="Action label (e.g., upscale1, variation2, reroll)")
    p_act.add_argument("origin_task_id", help="The task ID of the original image grid")
    p_act.add_argument("--nowait", action="store_true", help="Return immediately after submission")
    p_act.set_defaults(func=cmd_action)

    p_list = sub.add_parser("list", help="Show stored jobs")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(f"[CLI] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
