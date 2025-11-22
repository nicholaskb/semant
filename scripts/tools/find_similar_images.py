#!/usr/bin/env python3
from __future__ import annotations

"""
Utility script for indexing local images into Qdrant and running similarity search.

Examples:
    # Basic search (10 results, threshold 0.6)
    python scripts/tools/find_similar_images.py query.png

    # Index a directory before searching
    python scripts/tools/find_similar_images.py query.png --index-dir ./sample_images --top-k 10

    # Ingest only (no search)
    python scripts/tools/find_similar_images.py --index-dir ./dataset --skip-search

    # Run fully local similarity with traditional features (no OpenAI/Qdrant)
    python scripts/tools/find_similar_images.py query.png --index-dir ./dataset --engine local --top-k 5
"""

import argparse
import asyncio
import importlib
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from kg.services.image_embedding_service import ImageEmbeddingService
from kg.services.traditional_image_similarity import (
    TraditionalImageIndex,
    TraditionalFeatureExtractor,
)

try:  # Optional dependency used for progress bars
    tqdm_module = importlib.import_module("tqdm")
    tqdm = getattr(tqdm_module, "tqdm")
except (ImportError, AttributeError):  # pragma: no cover - optional dependency
    tqdm = None

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Index local images into Qdrant and search for similar images."
    )
    parser.add_argument(
        "query_image",
        nargs="?",
        type=Path,
        help="Path to the query image. Required unless --query-uri/--skip-search is set.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of similar images to return (default: 10).",
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=0.6,
        help="Minimum similarity score between 0-1 (default: 0.6).",
    )
    parser.add_argument(
        "--index-image",
        action="append",
        dest="index_images",
        type=Path,
        help="Image path to ingest before searching (can be used multiple times).",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        help="Directory of images to ingest before searching.",
    )
    parser.add_argument(
        "--index-limit",
        type=int,
        help="Maximum number of images to ingest from --index-dir.",
    )
    parser.add_argument(
        "--index-type",
        choices=["input", "output", "reference"],
        default="output",
        help='Value stored in metadata["image_type"] for ingested images (default: output).',
    )
    parser.add_argument(
        "--metadata-tag",
        action="append",
        default=[],
        help="Extra metadata key=value pair to attach to ingested images (can be passed multiple times).",
    )
    parser.add_argument(
        "--skip-search",
        action="store_true",
        help="Only ingest images (skip similarity search).",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable tqdm progress bar during ingestion (useful for CI/logs).",
    )
    parser.add_argument(
        "--query-uri",
        type=str,
        help="Use an existing image URI already stored in Qdrant as the query (no local file needed).",
    )
    parser.add_argument(
        "--engine",
        choices=["qdrant", "local"],
        default="qdrant",
        help="Similarity backend. Use 'local' for traditional CV features without Qdrant/OpenAI.",
    )
    parser.add_argument(
        "--local-cache",
        type=Path,
        help="Optional path to save/load a cached traditional feature index when --engine=local.",
    )
    parser.add_argument(
        "--rebuild-local",
        action="store_true",
        help="Force rebuilding the local cache even if --local-cache already exists.",
    )
    return parser


def _parse_metadata_tags(tags: Iterable[str]) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    for raw in tags:
        if "=" not in raw:
            raise ValueError(f"Metadata tag '{raw}' must be in key=value format")
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Metadata tag '{raw}' has empty key")
        metadata[key] = value
    return metadata


def _gather_index_targets(index_images: Iterable[Path], index_dir: Path | None, limit: int | None) -> List[Path]:
    targets: List[Path] = []
    for img in index_images or []:
        if not img.exists():
            print(f"⚠️  Skipping missing file: {img}")
            continue
        targets.append(img)
    if index_dir:
        if not index_dir.exists():
            print(f"⚠️  Index directory not found: {index_dir}")
        else:
            files = sorted(p for p in index_dir.rglob("*") if p.is_file())
            for file_path in files:
                if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                targets.append(file_path)
                if limit and len(targets) >= limit:
                    break
    return targets


def _load_or_build_local_index(
    image_paths: List[Path],
    cache_path: Optional[Path],
    force_rebuild: bool,
    use_progress: bool,
) -> TraditionalImageIndex:
    if cache_path and cache_path.exists() and not force_rebuild:
        print(f"\n📂 Loading cached traditional index from {cache_path}")
        return TraditionalImageIndex.load(cache_path, extractor=TraditionalFeatureExtractor())

    if not image_paths:
        raise ValueError("No images provided to build the local index.")

    extractor = TraditionalFeatureExtractor()
    index = TraditionalImageIndex(extractor)

    iterator = image_paths
    progress_bar = None
    if use_progress and tqdm:
        progress_bar = tqdm(image_paths, desc="Building local index", unit="image")
        iterator = progress_bar
    elif use_progress and not tqdm:
        print("⚠️  tqdm not installed; proceeding without local progress bar.")

    added = 0
    for path in iterator:
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            index.add_image(
                path,
                metadata={
                    "filename": path.name,
                    "source": "local_traditional_index",
                },
            )
            added += 1
        except Exception as exc:  # pylint: disable=broad-except
            print(f"   ❌ Failed to index {path}: {exc}")
    if progress_bar:
        progress_bar.close()

    if added == 0:
        raise RuntimeError("Could not index any images for the local engine.")

    index.finalize()

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        index.save(cache_path)

    print(f"\n✅ Local index ready ({added} images, {index.extractor.feature_size()} dims)")
    return index


def _convert_local_results(local_results: List[Dict[str, object]]) -> List[Dict[str, object]]:
    converted: List[Dict[str, object]] = []
    for result in local_results:
        metadata = dict(result.get("metadata") or {})
        image_path = result["image_path"]
        metadata.setdefault("image_path", image_path)
        converted.append(
            {
                "image_uri": metadata.get("image_uri", image_path),
                "score": result["score"],
                "metadata": metadata,
                "image_url": metadata.get("image_url", f"file://{image_path}"),
            }
        )
    return converted


def _run_local_mode(
    args: argparse.Namespace,
    targets: List[Path],
) -> None:
    print("\n" + "=" * 70)
    print("🧮 LOCAL TRADITIONAL IMAGE SIMILARITY")
    print("=" * 70)

    try:
        index = _load_or_build_local_index(
            image_paths=targets,
            cache_path=args.local_cache,
            force_rebuild=args.rebuild_local,
            use_progress=not args.no_progress,
        )
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Failed to prepare local index: {exc}")
        sys.exit(1)

    if args.skip_search:
        print("ℹ️  Local index built. Skipping search per --skip-search.")
        return

    query_path = args.query_image
    if not query_path or not query_path.exists():
        print(f"❌ Query image not found: {query_path}")
        sys.exit(1)

    print(f"\n🔍 Searching for top {args.top_k} similar images (local mode)...")
    try:
        local_results = index.search(query_path, top_k=args.top_k)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Failed to search local index: {exc}")
        sys.exit(1)

    filtered = [
        result for result in local_results if float(result["score"]) >= args.score_threshold
    ]
    converted = _convert_local_results(filtered)
    _print_results(converted)

    print("\n" + "=" * 70)
    print("✅ Local search complete!")
    print("=" * 70 + "\n")


async def _index_images(
    service: ImageEmbeddingService,
    image_paths: List[Path],
    image_type: str,
    extra_metadata: Dict[str, str],
    use_progress: bool,
) -> int:
    if not image_paths:
        return 0

    print("\n" + "=" * 70)
    print("📦 INDEXING LOCAL IMAGES INTO QDRANT")
    print("=" * 70)
    success_count = 0

    progress_bar = None
    progress_active = use_progress and bool(tqdm)
    if use_progress and not tqdm:
        print("⚠️  tqdm not installed. Run 'pip install tqdm' for progress bars (fallback to plain logs).")

    iterator = enumerate(image_paths, 1)
    if progress_active:
        progress_bar = tqdm(image_paths, desc="Indexing images", unit="image")
        iterator = enumerate(progress_bar, 1)

    for idx, image_path in iterator:
        if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            message = f"{idx:>3}. ⚠️  Skipping unsupported file: {image_path}"
            if progress_active:
                tqdm.write(message)
            else:
                print(message)
            continue

        if not image_path.exists():
            message = f"{idx:>3}. ⚠️  File not found: {image_path}"
            if progress_active:
                tqdm.write(message)
            else:
                print(message)
            continue

        if progress_active and progress_bar:
            progress_bar.set_postfix_str(image_path.name)
        else:
            print(f"{idx:>3}. 🖼️  {image_path}")
        try:
            embedding, description = await service.embed_image(image_path)
            metadata = {
                "filename": image_path.name,
                "image_type": image_type,
                "gcs_url": f"file://{image_path.resolve()}",
                "description": description,
                "source": "cli_find_similar_images",
                "indexed_at": datetime.utcnow().isoformat(),
            }
            metadata.update(extra_metadata)

            image_uri = f"http://example.org/local/{uuid.uuid4()}"
            service.store_embedding(
                image_uri=image_uri,
                embedding=embedding,
                metadata=metadata,
            )
            success_count += 1
            if not progress_active:
                print(f"     ✅ Stored as {image_uri}")
        except Exception as exc:  # pylint: disable=broad-except
            message = f"     ❌ Failed to index {image_path}: {exc}"
            if progress_active:
                tqdm.write(message)
            else:
                print(message)

    if progress_bar:
        progress_bar.close()

    print(f"\n✅ Indexed {success_count}/{len(image_paths)} local images into Qdrant\n")
    return success_count


def _print_results(results: List[Dict[str, object]]) -> None:
    print("=" * 70)
    print("📊 RESULTS")
    print("=" * 70)

    if not results:
        print("\n⚠️  No similar images found")
        print("   💡 Try:")
        print("      - Lowering score_threshold (e.g., 0.5)")
        print("      - Indexing more images first")
        print("      - Checking collection name: 'childrens_book_images'")
        return

    for i, result in enumerate(results, 1):
        score = float(result["score"])
        score_percent = score * 100
        bar_length = min(30, max(1, int(score * 30)))
        score_bar = "█" * bar_length + "░" * (30 - bar_length)

        if score >= 0.9:
            color = "🟢"
        elif score >= 0.8:
            color = "🟡"
        elif score >= 0.7:
            color = "🟠"
        else:
            color = "🔴"

        print(f"\n{color} Rank {i}: {result['image_uri']}")
        print(f"   Similarity: {score:.3f} ({score_percent:.1f}%)")
        print(f"   [{score_bar}]")

        metadata = result.get("metadata", {}) or {}
        if metadata:
            meta_pairs = ", ".join(f"{k}={v}" for k, v in metadata.items())
            print(f"   📋 Metadata: {meta_pairs}")
        image_url = result.get("image_url")
        if image_url:
            print(f"   🌐 image_url: {image_url}")


async def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.engine == "local":
        if args.query_uri:
            parser.error("--query-uri is not supported when --engine=local")
        if not args.skip_search and not args.query_image:
            parser.error("Provide a query image for local mode unless --skip-search is set.")
    else:
        if not args.skip_search and not (args.query_image or args.query_uri):
            parser.error("Provide a query image path or --query-uri unless --skip-search is set.")

    extra_metadata: Dict[str, str] = {}
    try:
        extra_metadata = _parse_metadata_tags(args.metadata_tag)
    except ValueError as exc:
        parser.error(str(exc))

    targets = _gather_index_targets(args.index_images, args.index_dir, args.index_limit)

    if args.engine == "local":
        _run_local_mode(args, targets)
        return

    try:
        print("📡 Connecting to Qdrant...")
        service = ImageEmbeddingService()
        print("   ✅ Connected to Qdrant")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Failed to initialize ImageEmbeddingService: {exc}")
        sys.exit(1)

    if targets:
        await _index_images(
            service,
            targets,
            args.index_type,
            extra_metadata,
            use_progress=not args.no_progress,
        )
    elif args.skip_search:
        print("⚠️  No images provided to index. Nothing to do.")

    if args.skip_search:
        return

    query_embedding: List[float]
    image_description: str

    if args.query_uri:
        print("\n" + "=" * 70)
        print("🔍 QDRANT IMAGE SIMILARITY SEARCH (Existing URI)")
        print("=" * 70)
        print(f"Query URI: {args.query_uri}")
        print(f"Top K: {args.top_k}")
        print(f"Score Threshold: {args.score_threshold}\n")

        try:
            query_embedding = service.get_embedding(args.query_uri)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"❌ Failed to retrieve embedding from Qdrant: {exc}")
            sys.exit(1)

        if not query_embedding:
            print(f"❌ No embedding found in Qdrant for {args.query_uri}")
            sys.exit(1)

        image_description = f"Existing Qdrant embedding for {args.query_uri}"
        print(f"   ✅ Retrieved embedding ({len(query_embedding)} dimensions)\n")
    else:
        query_path = args.query_image
        if not query_path or not query_path.exists():
            parser.error(f"Query image not found: {query_path}")

        print("\n" + "=" * 70)
        print("🔍 QDRANT IMAGE SIMILARITY SEARCH")
        print("=" * 70)
        print(f"Query Image: {query_path}")
        print(f"Top K: {args.top_k}")
        print(f"Score Threshold: {args.score_threshold}\n")

        try:
            print("🖼️  Generating embedding for query image...")
            query_embedding, image_description = await service.embed_image(query_path)
            print(f"   ✅ Generated embedding ({len(query_embedding)} dimensions)")
            print(f"   📝 Description: {image_description[:150]}...\n")
        except Exception as exc:
            print(f"❌ Failed to embed query image: {exc}")
            sys.exit(1)

    print(f"🔎 Searching for top {args.top_k} similar images...")
    try:
        results = service.search_similar_images(
            query_embedding=query_embedding,
            limit=args.top_k,
            score_threshold=args.score_threshold,
        )
    except Exception as exc:
        print(f"❌ Failed to search Qdrant: {exc}")
        sys.exit(1)

    print(f"   ✅ Found {len(results)} results\n")
    _print_results(results)

    print("\n" + "=" * 70)
    print("✅ Search complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

