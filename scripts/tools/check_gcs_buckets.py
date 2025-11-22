#!/usr/bin/env python3
"""
Check available Google Cloud Storage buckets and suggest a name for the brain_rot project.
"""
import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

def list_buckets():
    """List all accessible GCS buckets."""
    try:
        client = storage.Client()
        buckets = list(client.list_buckets())
        
        print("=" * 60)
        print("Available GCS Buckets:")
        print("=" * 60)
        
        if buckets:
            for bucket in buckets:
                print(f"  ✓ {bucket.name}")
                print(f"    Location: {bucket.location}")
                print(f"    Created: {bucket.time_created}")
                print()
        else:
            print("  (No buckets found or no access)")
        
        print("=" * 60)
        print("\nSuggested bucket names for 'brain_rot' project:")
        print("=" * 60)
        suggestions = [
            "brain-rot-content",
            "brainrot-trends",
            "italian-brainrot",
            "brainrot-viral",
            "trending-brainrot"
        ]
        
        for i, name in enumerate(suggestions, 1):
            print(f"  {i}. {name}")
        
        return buckets
        
    except Exception as e:
        print(f"Error accessing GCS: {e}")
        print("\nMake sure you have:")
        print("  1. Set GOOGLE_APPLICATION_CREDENTIALS")
        print("  2. Authenticated with: gcloud auth application-default login")
        return []

if __name__ == "__main__":
    list_buckets()

