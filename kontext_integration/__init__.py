"""
Kontext Integration package

This module mirrors the Midjourney integration structure but targets a
separate GoAPI-powered service referred to here as "Kontext". It provides a
typed async client, CLI entry-points, and a local scratch space for
investigation notes.

Environment variables (configure in .env):
  - KONTEXT_API_TOKEN                Required – GoAPI token (Bearer)
  - GOAPI_BASE_URL                   Optional – defaults to https://api.goapi.ai/api/v1
  - GCS_BUCKET_NAME                  Required for uploads
  - GOOGLE_APPLICATION_CREDENTIALS   Required for GCS auth (path to JSON)
"""

__all__ = [
    # Expose client and helper names for convenience
    "KontextClient",
    "KontextError",
    "upload_to_gcs_and_get_public_url",
]

from .client import KontextClient, KontextError, upload_to_gcs_and_get_public_url


