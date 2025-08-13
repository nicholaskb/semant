"""
Kontext Toolkit – CLI around GoAPI for the Kontext service.

This mirrors the midjourney_integration CLI for a consistent UX.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any

from .client import KontextClient, upload_to_gcs_and_get_public_url, poll_until_complete


def cmd_generate(args: argparse.Namespace) -> None:
    async def _run():
        client = KontextClient()

        image_url: str | None = None
        if args.image_path:
            image_path = Path(args.image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found at: {image_path}")
            image_url = upload_to_gcs_and_get_public_url(image_path, image_path.name)

        resp = await client.submit_generate(
            prompt=args.prompt,
            aspect_ratio=args.aspect_ratio,
            process_mode=args.mode,
            image_url=image_url,
        )

        task_id = resp.get("data", {}).get("task_id") or resp.get("task_id")
        if not task_id:
            print("Unexpected response:", resp)
            return

        if args.nowait:
            print(task_id)
            return

        final = await poll_until_complete(client, task_id)
        print(final)

    asyncio.run(_run())


def cmd_action(args: argparse.Namespace) -> None:
    async def _run():
        client = KontextClient()
        resp = await client.submit_action(args.task_id, action=args.action)
        print(resp)

    asyncio.run(_run())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Kontext via GoAPI (PPU)")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="Submit a generation task")
    g.add_argument("prompt", help="Text prompt")
    g.add_argument("--aspect_ratio", default="1:1")
    g.add_argument("--mode", choices=["relax", "fast", "turbo"], help="Process mode")
    g.add_argument("--image_path")
    g.add_argument("--nowait", action="store_true")
    g.set_defaults(func=cmd_generate)

    a = sub.add_parser("action", help="Submit an action on an existing task")
    a.add_argument("action", help="Action name, e.g., upscale1, reroll")
    a.add_argument("task_id", help="Origin task id")
    a.set_defaults(func=cmd_action)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()


