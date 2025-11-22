"""Example: Generate an image with MidjourneyClient.

Usage:
    python examples/midjourney_generate_image.py "A futuristic city skyline at dawn, digital art"

Environment variables:
    MIDJOURNEY_API_TOKEN   Your GoAPI Midjourney proxy token.

The script prints the final image URL to stdout.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import pathlib

# Ensure project root is on Python path when running the script directly
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from midjourney_integration import MidjourneyClient, MidjourneyError


async def _async_main(prompt: str, *, base_url: str | None = None) -> None:
    """Run the imagine request and print the resulting image URL."""
    # Ensure variables from .env are available (including MIDJOURNEY_API_TOKEN)
    load_dotenv()
    try:
        client = MidjourneyClient(base_url=base_url)
    except ValueError as exc:
        print(f"[midjourney-demo] Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        url = await client.imagine(prompt)
        print(url)
    except MidjourneyError as exc:
        print(f"[midjourney-demo] MidjourneyError: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001
        print(f"[midjourney-demo] Unexpected error: {exc}", file=sys.stderr)
        sys.exit(3)


def main() -> None:  # noqa: D401
    """CLI entry-point."""
    parser = argparse.ArgumentParser(description="Generate an image via MidjourneyClient")
    parser.add_argument("prompt", help="Text prompt describing the desired image")
    parser.add_argument(
        "--base-url",
        dest="base_url",
        required=False,
        help="Override the Midjourney API base URL if different from default",
    )
    args = parser.parse_args()

    asyncio.run(_async_main(args.prompt, base_url=args.base_url))


if __name__ == "__main__":
    main() 