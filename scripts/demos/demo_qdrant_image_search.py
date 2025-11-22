#!/usr/bin/env python3
"""
Quick Demo: Qdrant Image Similarity Search
Tests the /api/images/search-similar endpoint
"""

import asyncio
import sys
from pathlib import Path
import requests
from io import BytesIO
from PIL import Image
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from kg.services.image_embedding_service import ImageEmbeddingService


async def check_qdrant_connection():
    """Check if Qdrant is running"""
    try:
        service = ImageEmbeddingService()
        print("✅ Qdrant connection successful!")
        return True
    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
        print("\n💡 Make sure Qdrant is running:")
        print("   docker run -p 6333:6333 qdrant/qdrant")
        return False


async def demo_store_sample_images():
    """Store some sample images in Qdrant for testing"""
    print("\n📦 Storing sample images in Qdrant...")
    
    service = ImageEmbeddingService()
    
    # Sample image descriptions (simulating images)
    sample_images = [
        {
            "uri": "http://example.org/book/duck_pond.png",
            "description": "A yellow duckling with orange feet swimming in a blue pond with lily pads",
            "type": "input"
        },
        {
            "uri": "http://example.org/book/duck_watercolor.png",
            "description": "A yellow duck with orange feet in watercolor style, soft pastel colors",
            "type": "output"
        },
        {
            "uri": "http://example.org/book/duck_cartoon.png",
            "description": "A cute yellow duckling with big orange webbed feet, cartoon style",
            "type": "output"
        },
        {
            "uri": "http://example.org/book/fire_truck.png",
            "description": "A red fire truck with a ladder and siren, bright colors",
            "type": "output"
        },
        {
            "uri": "http://example.org/book/duck_family.png",
            "description": "A family of yellow ducklings with orange feet by a pond",
            "type": "output"
        }
    ]
    
    stored_count = 0
    for img in sample_images:
        try:
            # Generate embedding from description
            embedding = service.embed_text(img["description"])
            
            # Store in Qdrant
            service.store_embedding(
                image_uri=img["uri"],
                embedding=embedding,
                metadata={
                    "description": img["description"],
                    "type": img["type"]
                }
            )
            stored_count += 1
            print(f"   ✅ Stored: {img['uri']}")
        except Exception as e:
            print(f"   ⚠️  Failed to store {img['uri']}: {e}")
    
    print(f"\n✅ Stored {stored_count}/{len(sample_images)} images in Qdrant")
    return stored_count > 0


async def demo_search_similar():
    """Demo searching for similar images"""
    print("\n🔍 Testing similarity search...")
    
    service = ImageEmbeddingService()
    
    # Search query: similar to duckling
    query_text = "A yellow duckling with orange feet by a pond"
    print(f"   Query: '{query_text}'")
    
    # Generate query embedding
    query_embedding = service.embed_text(query_text)
    
    # Search for similar images
    results = service.search_similar_images(
        query_embedding=query_embedding,
        limit=5,
        score_threshold=0.5
    )
    
    print(f"\n   Found {len(results)} similar images:")
    for i, result in enumerate(results, 1):
        score_percent = result["score"] * 100
        img_type = result["metadata"].get("type", "unknown")
        description = result["metadata"].get("description", "")[:60]
        print(f"   {i}. Score: {score_percent:.1f}% | Type: {img_type}")
        print(f"      URI: {result['image_uri']}")
        print(f"      Desc: {description}...")
    
    return len(results) > 0


async def demo_api_endpoint():
    """Test the API endpoint directly"""
    print("\n🌐 Testing API endpoint /api/images/search-similar...")
    
    # Create a simple test image
    img = Image.new('RGB', (200, 200), color='yellow')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Prepare request
    files = {'image_file': ('test_duck.png', img_bytes, 'image/png')}
    data = {
        'limit': '5',
        'score_threshold': '0.5'
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/api/images/search-similar',
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ API endpoint working!")
            print(f"   Query description: {result.get('query_image', 'N/A')[:100]}...")
            print(f"   Found {result.get('total_found', 0)} similar images")
            
            if result.get('results'):
                print(f"\n   Top result:")
                top = result['results'][0]
                print(f"      Score: {top['score']*100:.1f}%")
                print(f"      URI: {top['image_uri']}")
            
            return True
        else:
            print(f"   ❌ API returned status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ⚠️  API server not running. Start it with: python main.py")
        return False
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
        return False


async def main():
    """Run the demo"""
    print("=" * 60)
    print("🎨 QDRANT IMAGE SIMILARITY SEARCH DEMO")
    print("=" * 60)
    
    # Step 1: Check Qdrant connection
    if not await check_qdrant_connection():
        return
    
    # Step 2: Store sample images
    if not await demo_store_sample_images():
        print("\n⚠️  No images stored. Continuing anyway...")
    
    # Step 3: Test direct search
    await demo_search_similar()
    
    # Step 4: Test API endpoint
    print("\n" + "=" * 60)
    print("📡 Testing API Endpoint")
    print("=" * 60)
    await demo_api_endpoint()
    
    print("\n" + "=" * 60)
    print("✅ DEMO COMPLETE!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("   1. Start API server: python main.py")
    print("   2. Open browser: http://localhost:8000/static/frontend_image_search_example.html")
    print("   3. Upload an image and search for similar ones!")


if __name__ == "__main__":
    asyncio.run(main())

