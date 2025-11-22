#!/usr/bin/env python3
"""CLI entry point for the children's book workflow."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to Python path (required for semant imports)
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table

from semant.workflows.childrens_book.orchestrator import ChildrensBookOrchestrator


async def main() -> None:
    """Parse CLI arguments and run the workflow."""
    parser = argparse.ArgumentParser(
        description="Generate a children's book from input/output image pairs."
    )
    parser.add_argument("--bucket", help="GCS bucket name")
    parser.add_argument(
        "--input-prefix",
        default="book_illustrations/",
        help="Input images prefix (default: book_illustrations/)",
    )
    parser.add_argument(
        "--output-prefix",
        default="midjourney/",
        help="Output images prefix (default: midjourney/)",
    )
    parser.add_argument(
        "--extensions",
        nargs="*",
        help="File extensions (e.g., png jpg)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--max-downloads",
        type=int,
        default=8,
        help="Max concurrent downloads/embeds to limit API spend",
    )

    args = parser.parse_args()

    orchestrator = None
    console = Console()
    try:
        orchestrator = ChildrensBookOrchestrator(
            bucket_name=args.bucket,
            input_prefix=args.input_prefix,
            output_prefix=args.output_prefix,
            max_concurrent_downloads=args.max_downloads,
        )
        await orchestrator.initialize()
        result = await orchestrator.generate_book(
            extensions=args.extensions,
            overwrite=args.overwrite,
        )

        table = Table(title="Book Generation Summary")
        table.add_column("Step", style="cyan")
        table.add_column("Result", style="green")

        table.add_row(
            "Images Ingested",
            str(result.get("ingestion", {}).get("successful", 0)),
        )
        table.add_row(
            "Pairs Created",
            str(result.get("pairing", {}).get("pairs_count", 0)),
        )
        table.add_row(
            "Pages Designed",
            str(len(result.get("layouts", {}).get("layouts", []))),
        )
        table.add_row("HTML Generated", result.get("book", {}).get("html_path", "N/A"))

        console.print(table)

        html_path = result.get("book", {}).get("html_path")
        if html_path and Path(html_path).exists():
            console.print(f"\n[bold green]✅ Opening book: {html_path}[/bold green]")
            import subprocess

            subprocess.run(["open", html_path])
    finally:
        if orchestrator and getattr(orchestrator, "kg_manager", None):
            try:
                await orchestrator.kg_manager.shutdown()
            except Exception:
                console.print("[yellow]Warning: failed to shut down KG manager[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())
