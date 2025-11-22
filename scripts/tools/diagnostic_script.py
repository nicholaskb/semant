#!/usr/bin/env python3
"""
Diagnostic script to identify why images aren't showing.
Run this to check each potential issue.
"""

import sys
from pathlib import Path

print("=" * 70)
print("IMAGE DISPLAY DIAGNOSTIC SCRIPT")
print("=" * 70)
print()

# Check 1: Can we connect to Qdrant?
print("1. Checking Qdrant connection...")
try:
    from qdrant_client import QdrantClient
    client = QdrantClient(host="localhost", port=6333)
    collections = client.get_collections()
    print(f"   ✅ Qdrant connected")
    print(f"   Collections: {[c.name for c in collections.collections]}")
except Exception as e:
    print(f"   ❌ Cannot connect to Qdrant: {e}")
    print("   → Start Qdrant: docker-compose up -d qdrant")
    sys.exit(1)

# Check 2: What's in Qdrant metadata?
print("\n2. Checking Qdrant metadata structure...")
try:
    from qdrant_client import QdrantClient
    client = QdrantClient(host="localhost", port=6333)
    
    # Get sample points
    points, _ = client.scroll(
        collection_name="childrens_book_images",
        limit=3,
        with_payload=True
    )
    
    if not points:
        print("   ⚠️  No images in Qdrant collection")
        print("   → Need to ingest images first")
    else:
        print(f"   ✅ Found {len(points)} sample images")
        for i, point in enumerate(points, 1):
            print(f"\n   Sample {i}:")
            print(f"      Point ID: {point.id}")
            payload = point.payload
            print(f"      image_uri: {payload.get('image_uri', 'MISSING')}")
            print(f"      gcs_url: {payload.get('gcs_url', 'MISSING')}")
            print(f"      filename: {payload.get('filename', 'MISSING')}")
            
            if 'gcs_url' not in payload:
                print(f"      ⚠️  MISSING gcs_url in metadata!")
            else:
                gcs_url = payload['gcs_url']
                if gcs_url.startswith('gs://'):
                    public_url = f"https://storage.googleapis.com/{gcs_url[5:]}"
                    print(f"      Converted URL: {public_url}")
                    print(f"      → Test with: curl -I '{public_url}'")
except Exception as e:
    print(f"   ❌ Error checking metadata: {e}")
    import traceback
    traceback.print_exc()

# Check 3: Test service method
print("\n3. Testing ImageEmbeddingService.search_similar_images()...")
try:
    from kg.services.image_embedding_service import ImageEmbeddingService
    import asyncio
    
    service = ImageEmbeddingService()
    
    # Create a dummy embedding
    dummy_embedding = [0.1] * 1536
    
    results = service.search_similar_images(
        query_embedding=dummy_embedding,
        limit=3
    )
    
    if not results:
        print("   ⚠️  No search results (expected if no images)")
    else:
        print(f"   ✅ Service returns {len(results)} results")
        for i, result in enumerate(results[:2], 1):
            print(f"\n   Result {i}:")
            print(f"      image_uri: {result.get('image_uri', 'MISSING')}")
            print(f"      image_url: {result.get('image_url', 'MISSING')}")
            print(f"      score: {result.get('score', 0)}")
            
            image_url = result.get('image_url', '')
            if not image_url:
                print(f"      ❌ MISSING image_url field!")
            elif image_url.startswith('http://example.org'):
                print(f"      ⚠️  image_url is still placeholder")
            elif image_url.startswith('https://storage.googleapis.com'):
                print(f"      ✅ image_url is GCS public URL format")
            else:
                print(f"      ⚠️  image_url format: {image_url[:50]}")
except Exception as e:
    print(f"   ❌ Error testing service: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("1. If gcs_url missing: Re-ingest images")
print("2. If image_url missing: Check service conversion logic")
print("3. If URLs exist but don't load: Test GCS public access")
print("4. Run: curl -I 'https://storage.googleapis.com/BUCKET/path.jpg'")
