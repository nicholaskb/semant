#!/usr/bin/env python3
"""
Unit test for the GCS URL conversion function.
Tests the _convert_gcs_url_to_public function logic.
"""

import sys
from pathlib import Path

# Add parent directory to path to import from main.py
sys.path.insert(0, str(Path(__file__).parent))

# Import the conversion function
# We'll need to extract it or test it directly
def convert_gcs_url_to_public(gcs_url: str) -> str:
    """
    Convert a gs:// URL to a public HTTP URL.
    (Copied from main.py for testing)
    """
    if not gcs_url:
        return gcs_url
    
    # Convert gs://bucket/path to https://storage.googleapis.com/bucket/path
    if gcs_url.startswith("gs://"):
        path = gcs_url[5:]  # Remove "gs://" prefix
        return f"https://storage.googleapis.com/{path}"
    
    # Handle file:// URLs (for local development)
    if gcs_url.startswith("file://"):
        file_path = gcs_url[7:]  # Remove "file://" prefix
        return gcs_url
    
    # Already an HTTP URL or unknown format
    return gcs_url

def test_conversion():
    """Test the URL conversion function"""
    print("=" * 70)
    print("🧪 UNIT TEST: GCS URL Conversion")
    print("=" * 70)
    print()
    
    test_cases = [
        # (input, expected_output, description)
        (
            "gs://my-bucket/path/to/image.png",
            "https://storage.googleapis.com/my-bucket/path/to/image.png",
            "Standard gs:// URL"
        ),
        (
            "gs://bucket-name/subfolder/file.jpg",
            "https://storage.googleapis.com/bucket-name/subfolder/file.jpg",
            "gs:// URL with subfolder"
        ),
        (
            "https://storage.googleapis.com/bucket/image.png",
            "https://storage.googleapis.com/bucket/image.png",
            "Already HTTP URL (should pass through)"
        ),
        (
            "file:///local/path/image.png",
            "file:///local/path/image.png",
            "file:// URL (local dev)"
        ),
        (
            "",
            "",
            "Empty string"
        ),
        (
            "http://example.org/image/123",
            "http://example.org/image/123",
            "Other HTTP URL (pass through)"
        ),
    ]
    
    all_passed = True
    
    for i, (input_url, expected, description) in enumerate(test_cases, 1):
        result = convert_gcs_url_to_public(input_url)
        passed = result == expected
        
        status = "✅" if passed else "❌"
        print(f"{status} Test {i}: {description}")
        print(f"   Input:    {input_url}")
        print(f"   Expected:  {expected}")
        print(f"   Got:       {result}")
        
        if not passed:
            all_passed = False
            print(f"   ⚠️  MISMATCH!")
        print()
    
    print("=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = test_conversion()
    exit(0 if success else 1)

