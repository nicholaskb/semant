#!/usr/bin/env python3
"""
Create GCS bucket structure for Brain Rot project.

This script creates the 'brainrot-trends' bucket (if it doesn't exist) and
sets up the directory structure for storing trending topics, tokenized data,
combinations, and generated images.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.cloud import storage
from loguru import logger

try:
    from google.cloud.exceptions import Conflict
    CONFLICT_AVAILABLE = True
except ImportError:
    CONFLICT_AVAILABLE = False
    # Fallback: use generic Exception
    Conflict = Exception

load_dotenv()

# Bucket name
BUCKET_NAME = "brainrot-trends"

# Directory structure to create
DIRECTORIES = [
    "us_trends/raw",
    "us_trends/tokenized",
    "us_trends/selected",
    "italian_trends/raw",
    "italian_trends/tokenized",
    "italian_trends/phrases",
    "combinations/ai_selections",
    "combinations/final",
    "generated_images",
]


def create_bucket_if_not_exists(client: storage.Client, bucket_name: str) -> storage.Bucket:
    """Create GCS bucket if it doesn't exist."""
    try:
        bucket = client.create_bucket(bucket_name)
        logger.info(f"✅ Created bucket: {bucket_name}")
        return bucket
    except Exception as e:
        # Check if it's a conflict error (bucket already exists)
        error_str = str(e).lower()
        if 'already exists' in error_str or '409' in error_str or 'conflict' in error_str:
            logger.info(f"ℹ️  Bucket {bucket_name} already exists")
            return client.bucket(bucket_name)
        else:
            logger.error(f"❌ Failed to create bucket: {e}")
            raise


def create_directory_structure(bucket: storage.Bucket, directories: list):
    """Create directory structure by uploading placeholder files."""
    created_count = 0
    
    for directory in directories:
        # GCS doesn't have true directories, so we create placeholder files
        placeholder_path = f"{directory}/.gitkeep"
        
        try:
            blob = bucket.blob(placeholder_path)
            blob.upload_from_string(
                f"# Placeholder for {directory}\n",
                content_type="text/plain"
            )
            logger.debug(f"  Created: {placeholder_path}")
            created_count += 1
        except Exception as e:
            logger.warning(f"  Failed to create {placeholder_path}: {e}")
    
    logger.info(f"✅ Created {created_count}/{len(directories)} directory placeholders")


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Brain Rot GCS Structure Setup")
    logger.info("=" * 60)
    
    # Check for credentials
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        logger.warning("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set")
        logger.info("Attempting to use Application Default Credentials...")
    
    try:
        # Initialize GCS client
        client = storage.Client()
        project_id = client.project
        logger.info(f"📦 Project: {project_id}")
        logger.info(f"🪣 Target bucket: {BUCKET_NAME}")
        logger.info("")
        
        # Create bucket if it doesn't exist
        logger.info("Step 1: Creating bucket (if needed)...")
        bucket = create_bucket_if_not_exists(client, BUCKET_NAME)
        logger.info("")
        
        # Create directory structure
        logger.info("Step 2: Creating directory structure...")
        create_directory_structure(bucket, DIRECTORIES)
        logger.info("")
        
        # Verify structure
        logger.info("Step 3: Verifying structure...")
        blobs = list(bucket.list_blobs(prefix="", delimiter="/"))
        logger.info(f"✅ Found {len(blobs)} items in bucket")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Setup complete!")
        logger.info("=" * 60)
        logger.info(f"Bucket: gs://{BUCKET_NAME}")
        logger.info(f"Directories created: {len(DIRECTORIES)}")
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        logger.info("")
        logger.info("Troubleshooting:")
        logger.info("1. Ensure GOOGLE_APPLICATION_CREDENTIALS is set")
        logger.info("2. Run: gcloud auth application-default login")
        logger.info("3. Verify you have Storage Admin permissions")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

