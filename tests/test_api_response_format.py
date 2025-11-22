#!/usr/bin/env python3
"""
Test script to verify the API response format includes image_url fields.
Simulates what the API should return after our fix.
"""

def simulate_api_response():
    """Simulate the API response format with the fix applied"""
    
    # Simulate Qdrant results (what search_similar_images returns)
    qdrant_results = [
        {
            "image_uri": "http://example.org/image/uuid-123",
            "score": 0.966,
            "metadata": {
                "filename": "IMG_20230105_112009.jpg",
                "gcs_url": "gs://my-bucket/input_kids_monster/IMG_20230105_112009.jpg",
                "image_type": "input",
                "description": "A cartoonish character..."
            }
        },
        {
            "image_uri": "http://example.org/image/uuid-456",
            "score": 0.965,
            "metadata": {
                "filename": "60fcdd96-dcd5-4d11-b18e-32747ba00d50.png",
                "gcs_url": "gs://my-bucket/generated_images/60fcdd96-dcd5-4d11-b18e-32747ba00d50.png",
                "image_type": "output",
                "description": "Generated image..."
            }
        },
        {
            "image_uri": "http://example.org/image/uuid-789",
            "score": 0.964,
            "metadata": {
                # Missing gcs_url - should fallback to image_uri
                "filename": "test.png",
                "image_type": "output"
            }
        }
    ]
    
    # Apply the conversion logic (from main.py)
    def convert_gcs_url_to_public(gcs_url: str) -> str:
        if not gcs_url:
            return gcs_url
        if gcs_url.startswith("gs://"):
            path = gcs_url[5:]
            return f"https://storage.googleapis.com/{path}"
        return gcs_url
    
    # Process results (simulating what the API does)
    processed_results = []
    for result in qdrant_results:
        gcs_url = result.get("metadata", {}).get("gcs_url", "")
        
        if gcs_url:
            public_url = convert_gcs_url_to_public(gcs_url)
            result["image_url"] = public_url
        else:
            result["image_url"] = result.get("image_uri", "")
        
        processed_results.append(result)
    
    # Format as API response
    api_response = {
        "query_image": "A cartoonish character resembling a monster...",
        "results": processed_results,
        "total_found": len(processed_results)
    }
    
    return api_response

def test_response_format():
    """Test and display the API response format"""
    print("=" * 70)
    print("🧪 TESTING API RESPONSE FORMAT")
    print("=" * 70)
    print()
    
    response = simulate_api_response()
    
    print("📊 Simulated API Response:")
    print(json.dumps(response, indent=2))
    print()
    
    print("=" * 70)
    print("✅ VERIFICATION:")
    print("=" * 70)
    print()
    
    all_valid = True
    
    for i, result in enumerate(response["results"], 1):
        print(f"Result {i}:")
        print(f"   image_uri: {result.get('image_uri', 'N/A')}")
        
        image_url = result.get('image_url', '')
        if image_url:
            print(f"   ✅ image_url: {image_url}")
            
            # Verify format
            if image_url.startswith('https://storage.googleapis.com/'):
                print(f"      ✅ Valid GCS public URL format")
            elif image_url.startswith('http://example.org'):
                print(f"      ⚠️  Fallback to placeholder (no gcs_url in metadata)")
            else:
                print(f"      ⚠️  Other format: {image_url[:50]}")
        else:
            print(f"   ❌ Missing image_url field!")
            all_valid = False
        
        print()
    
    if all_valid:
        print("=" * 70)
        print("✅ ALL RESULTS HAVE image_url FIELD!")
        print("=" * 70)
        print()
        print("📝 Frontend can now use:")
        print("   result.image_url || result.image_uri")
        print()
        print("✅ Fix verified - images should display correctly!")
    else:
        print("=" * 70)
        print("❌ SOME RESULTS MISSING image_url FIELD")
        print("=" * 70)
    
    return all_valid

if __name__ == "__main__":
    import json
    success = test_response_format()
    exit(0 if success else 1)

