"""
One-call script: upload 6 persona photos and generate a themed set of images.

Usage:
  python -m examples.persona_batch_generate \
    --theme "Lord of the Rings" \
    --version v7 \
    --count 10 \
    /abs/path/child1.png /abs/path/child2.png /abs/path/child3.png \
    /abs/path/child4.png /abs/path/child5.png /abs/path/child6.png

Env required:
  MIDJOURNEY_API_TOKEN, GCS_BUCKET_NAME, GOOGLE_APPLICATION_CREDENTIALS
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from midjourney_integration.client import (
    upload_to_gcs_and_get_public_url,
    verify_image_is_public,
)
from semant.agent_tools.midjourney.workflows import generate_themed_portraits


async def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Upload 6 persona images, generate themed set")
    parser.add_argument("images", nargs=6, help="Exactly 6 local image file paths")
    parser.add_argument("--theme", required=True, help="Theme text (e.g., 'Lord of the Rings')")
    parser.add_argument("--version", default="v7", help="Model version: v7 or v6")
    parser.add_argument("--count", type=int, default=10, help="Number of final images to generate")
    args = parser.parse_args()

    image_paths: List[Path] = [Path(p).expanduser().resolve() for p in args.images]
    for p in image_paths:
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

    print("Uploading 6 images to GCS…")
    uploaded_urls: List[str] = []
    for p in image_paths:
        public_url = upload_to_gcs_and_get_public_url(p, p.name)
        await verify_image_is_public(public_url)
        uploaded_urls.append(public_url)
        print(f"  ✔ {p.name} → {public_url}")

    print("Generating themed images…")
    results = await generate_themed_portraits(
        image_urls=uploaded_urls,
        theme=args.theme,
        model_version=args.version,
        num_images=args.count,
    )

    # Normalize output
    if isinstance(results, dict) and "image_urls" in results:
        urls = results["image_urls"]
    elif isinstance(results, list):
        urls = results
    else:
        urls = [str(results)]

    print("\nFinal URLs:")
    for u in urls:
        print(u)


if __name__ == "__main__":
    asyncio.run(main())



