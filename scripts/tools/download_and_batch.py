#!/usr/bin/env python3

"""
Download kids_monsters input images and generated outputs from Google Cloud Storage,
then automatically split them into manageable batches for Apple Photos upload.

Run this script on your LOCAL MACHINE (not on Google Cloud).

Requirements:
- Python 3.8+
- pip install google-cloud-storage python-dotenv

Setup:
1. Set your GCS_BUCKET_NAME environment variable
2. Set up Google Cloud credentials (gcloud auth application-default login)
   OR set GOOGLE_APPLICATION_CREDENTIALS to your service account key file

Usage:
    python3 download_and_batch.py
    python3 download_and_batch.py --batch-size 200
    python3 download_and_batch.py --input-only
    python3 download_and_batch.py --output-only
    python3 download_and_batch.py --overwrite
"""

import argparse
import os
import shutil
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

from dotenv import load_dotenv
from google.cloud import storage
from google.cloud.exceptions import NotFound

# Load environment variables
load_dotenv()


def log(message: str) -> None:
    print(message, flush=True)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def iter_blob_names(
    bucket: storage.Bucket,
    prefix: str,
    extensions: Optional[Sequence[str]] = None,
) -> Iterable[str]:
    normalized_extensions: Optional[Tuple[str, ...]] = None
    if extensions:
        normalized_extensions = tuple(ext.lower().lstrip(".") for ext in extensions)

    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith("/"):
            continue
        if normalized_extensions:
            suffix = Path(blob.name).suffix.lower().lstrip(".")
            if suffix not in normalized_extensions:
                continue
        yield blob.name


def download_file(
    bucket: storage.Bucket,
    blob_name: str,
    destination_dir: Path,
    overwrite: bool = False,
) -> bool:
    destination = destination_dir / Path(blob_name).name

    if destination.exists() and not overwrite:
        log(f"⏭️  Skipping {destination.name} (already exists)")
        return False

    blob = bucket.blob(blob_name)

    try:
        blob.download_to_filename(str(destination))
    except NotFound:
        log(f"❌ Not found in bucket: {blob_name}")
        return False
    except Exception as exc:
        log(f"❌ Failed to download {blob_name}: {exc}")
        return False

    log(f"✅ Downloaded {destination.name} ({destination.stat().st_size:,} bytes)")
    return True


def download_folder(
    bucket: storage.Bucket,
    prefix: str,
    output_dir: Path,
    overwrite: bool = False,
    extensions: Optional[Sequence[str]] = None,
) -> Tuple[int, int, int]:
    ensure_directory(output_dir)
    total = skipped = failed = 0

    for blob_name in iter_blob_names(bucket, prefix, extensions):
        total += 1
        if download_file(bucket, blob_name, output_dir, overwrite=overwrite):
            continue
        if (output_dir / Path(blob_name).name).exists():
            skipped += 1
        else:
            failed += 1

    return total, skipped, failed


def create_upload_batches(source_dir: Path, batch_size: int = 200, upload_dir: Path = None) -> dict:
    """Split downloaded images into batches for Apple Photos upload."""
    if upload_dir is None:
        upload_dir = source_dir.parent / "uploads"

    # Clean existing upload directory
    if upload_dir.exists():
        shutil.rmtree(upload_dir)

    ensure_directory(upload_dir)

    # Get all image files
    image_extensions = ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp"]
    all_images = []
    for ext in image_extensions:
        all_images.extend(source_dir.glob(ext))

    all_images.sort()  # Sort for consistent batching

    if not all_images:
        log(f"⚠️  No image files found in {source_dir}")
        return {}

    total_images = len(all_images)
    num_batches = (total_images + batch_size - 1) // batch_size  # Ceiling division

    log(f"📦 Splitting {total_images} images into {num_batches} batches of ~{batch_size} files each")

    batches = {}

    for batch_num in range(1, num_batches + 1):
        batch_name = f"batch_{batch_num:02d}"
        batch_dir = upload_dir / batch_name
        ensure_directory(batch_dir)

        start_idx = (batch_num - 1) * batch_size
        end_idx = min(batch_num * batch_size, total_images)
        batch_files = all_images[start_idx:end_idx]

        moved_count = 0
        for src_file in batch_files:
            dst_file = batch_dir / src_file.name
            shutil.move(str(src_file), str(dst_file))
            moved_count += 1

        batches[batch_name] = moved_count
        log(f"   📁 {batch_name}: {moved_count} files")

    return batches


def organize_by_type(source_dir: Path, upload_dir: Path) -> dict:
    """Organize images by type (input vs generated) for separate upload batches."""
    ensure_directory(upload_dir)

    # Separate input and generated images
    input_dir = upload_dir / "input_images"
    generated_dir = upload_dir / "generated_images"

    ensure_directory(input_dir)
    ensure_directory(generated_dir)

    # Move files based on naming patterns
    moved_counts = {"input": 0, "generated": 0}

    for file_path in source_dir.iterdir():
        if not file_path.is_file():
            continue

        if file_path.name.startswith("IMG_") or file_path.suffix.lower() == ".jpg":
            # Input images (original kid photos)
            shutil.move(str(file_path), str(input_dir / file_path.name))
            moved_counts["input"] += 1
        elif (
            file_path.name.startswith("imagen_")
            or file_path.name.startswith("gen_")
            or file_path.name.startswith("upscaled_")
        ):
            # Generated images (AI-generated content)
            shutil.move(str(file_path), str(generated_dir / file_path.name))
            moved_counts["generated"] += 1
        else:
            # Other files - put in input by default
            shutil.move(str(file_path), str(input_dir / file_path.name))
            moved_counts["input"] += 1

    return moved_counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download kids_monsters images from GCS and split into Apple Photos upload batches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download and batch all images (default batch size: 200)
  python3 download_and_batch.py

  # Custom batch size
  python3 download_and_batch.py --batch-size 200

  # Download only input images
  python3 download_and_batch.py --input-only

  # Download only generated outputs
  python3 download_and_batch.py --output-only

  # Overwrite existing files
  python3 download_and_batch.py --overwrite

  # Custom output directory
  python3 download_and_batch.py --output-dir ./my_downloads
        """,
    )

    # Bucket configuration
    default_bucket = os.getenv("GCS_BUCKET_NAME", "veo-videos-baro-1759717316")
    parser.add_argument(
        "--bucket",
        default=default_bucket,
        help=f"GCS bucket name (default: {default_bucket})",
    )

    # What to download
    parser.add_argument(
        "--input-only",
        action="store_true",
        help="Download only input images (kids_monsters)",
    )
    parser.add_argument(
        "--output-only",
        action="store_true",
        help="Download only generated outputs",
    )

    # Input configuration
    parser.add_argument(
        "--input-prefix",
        default="input_kids_monster/",
        help="GCS prefix for input images (default: input_kids_monster/)",
    )
    parser.add_argument(
        "--output-prefix",
        default="generated_images/",
        help="GCS prefix for generated outputs (default: generated_images/)",
    )

    # Output directories
    parser.add_argument(
        "--output-dir",
        default="downloads",
        help="Base directory for downloads (default: downloads/)",
    )
    parser.add_argument(
        "--upload-dir",
        help="Directory for upload batches (defaults to output-dir/../uploads)",
    )

    # Batch configuration
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Number of images per upload batch (default: 200)",
    )
    parser.add_argument(
        "--organize-by-type",
        action="store_true",
        help="Organize into input_images/ and generated_images/ folders instead of batches",
    )

    # Options
    parser.add_argument(
        "--extensions",
        nargs="*",
        help="Optional list of file extensions to download (e.g. png jpg)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files that already exist locally",
    )

    args = parser.parse_args()

    # Validate mutually exclusive options
    if args.input_only and args.output_only:
        parser.error("--input-only and --output-only are mutually exclusive")

    # Determine what to download
    download_inputs = not args.output_only
    download_outputs = not args.input_only

    # Set up directories
    base_dir = Path(args.output_dir)
    download_dir = base_dir / "all_images"
    upload_dir = Path(args.upload_dir) if args.upload_dir else base_dir.parent / "uploads"

    log("=" * 80)
    log("DOWNLOADING FROM GOOGLE CLOUD STORAGE & CREATING UPLOAD BATCHES")
    log("=" * 80)
    log("")

    log(f"Bucket: {args.bucket}")
    log(f"Download inputs: {'yes' if download_inputs else 'no'}")
    log(f"Download outputs: {'yes' if download_outputs else 'no'}")
    if args.organize_by_type:
        log("Organization: by type (input_images/ and generated_images/)")
    else:
        log(f"Organization: batches of {args.batch_size} images each")
    if args.extensions:
        log(f"Extensions filter: {', '.join(args.extensions)}")
    log(f"Overwrite existing: {'yes' if args.overwrite else 'no'}")
    log(f"Download directory: {download_dir}")
    log(f"Upload directory: {upload_dir}")
    log("")

    # Check Google Cloud authentication
    try:
        client = storage.Client()
        bucket = client.bucket(args.bucket)
        # Test bucket access
        bucket.reload()
        log(f"✅ Connected to GCS bucket: {args.bucket}")
    except Exception as e:
        log(f"❌ Failed to connect to GCS: {e}")
        log("")
        log("Please ensure:")
        log("1. You have authenticated with Google Cloud:")
        log("   gcloud auth application-default login")
        log("")
        log("2. OR set GOOGLE_APPLICATION_CREDENTIALS to your service account key:")
        log("   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
        log("")
        log("3. The bucket name is correct and you have access")
        return 1

    total_downloaded = 0
    total_skipped = 0
    total_failed = 0

    # Download input images
    if download_inputs:
        log("📥 Downloading input kids images...")
        total, skipped, failed = download_folder(
            bucket,
            prefix=args.input_prefix,
            output_dir=download_dir,
            overwrite=args.overwrite,
            extensions=args.extensions,
        )
        log(
            f"   Summary (inputs): total={total}, "
            f"downloaded={total - skipped - failed}, "
            f"skipped={skipped}, failed={failed}"
        )
        total_downloaded += total - skipped - failed
        total_skipped += skipped
        total_failed += failed
        log("")

    # Download generated outputs
    if download_outputs:
        log("📥 Downloading generated outputs...")
        total, skipped, failed = download_folder(
            bucket,
            prefix=args.output_prefix,
            output_dir=download_dir,
            overwrite=args.overwrite,
            extensions=args.extensions,
        )
        log(
            f"   Summary (outputs): total={total}, "
            f"downloaded={total - skipped - failed}, "
            f"skipped={skipped}, failed={failed}"
        )
        total_downloaded += total - skipped - failed
        total_skipped += skipped
        total_failed += failed
        log("")

    # Create upload batches
    if total_downloaded > 0:
        log("📦 Creating upload batches for Apple Photos...")

        if args.organize_by_type:
            counts = organize_by_type(download_dir, upload_dir)
            log(f"   📁 input_images: {counts['input']} files")
            log(f"   📁 generated_images: {counts['generated']} files")
        else:
            batches = create_upload_batches(download_dir, args.batch_size, upload_dir)
            total_batched = sum(batches.values())
            log(f"   📦 Created {len(batches)} batches with {total_batched} files total")

        # Clean up the temporary download directory
        if download_dir.exists():
            shutil.rmtree(download_dir)
            log(f"   🧹 Cleaned up temporary download directory")

        log("")

    # Final summary
    log("=" * 80)
    log("DOWNLOAD & BATCHING COMPLETE")
    log("=" * 80)
    log(f"✅ Successfully downloaded: {total_downloaded}")
    log(f"⏭️  Skipped (already exists): {total_skipped}")
    log(f"❌ Failed: {total_failed}")
    log("")

    if total_downloaded > 0:
        log("📁 Upload batches ready in:")
        log(f"   {upload_dir.absolute()}")
        log("")
        log("🎯 Apple Photos Upload Instructions:")
        log("   1. Open Apple Photos app")
        log("   2. Upload one batch folder at a time")
        log("   3. Drag files into Photos or use File → Import → From Folder")
        log("   4. Wait for each batch to complete before starting the next")
        log("")
        if args.organize_by_type:
            log("   📁 Upload input_images/ first, then generated_images/")
        else:
            log(f"   📦 Upload batch_01/ through batch_{len(batches):02d}/ sequentially")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        raise SystemExit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        raise SystemExit(1)

