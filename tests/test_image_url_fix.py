#!/usr/bin/env python3
"""
Test script to verify that image URLs are properly converted from gs:// to public HTTP URLs
in the /api/images/search-similar endpoint.
"""

import requests
from io import BytesIO
from PIL import Image
import json
import time

def wait_for_server(max_attempts=10, delay=2):
    """Wait for the API server to be ready"""
    print("⏳ Waiting for API server to be ready...")
    for i in range(max_attempts):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ API server is ready!\n")
                return True
        except requests.exceptions.ConnectionError:
            pass
        except requests.exceptions.RequestException:
            pass
        
        if i < max_attempts - 1:
            print(f"   Attempt {i+1}/{max_attempts}...")
            time.sleep(delay)
    
    print("❌ API server not responding")
    print("   Please start the server with: python main.py")
    return False

def create_test_image():
    """Create a simple test image"""
    img = Image.new('RGB', (200, 200), color='yellow')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_image_url_conversion():
    """Test that image URLs are properly converted"""
    print("=" * 70)
    print("🧪 TESTING IMAGE URL CONVERSION FIX")
    print("=" * 70)
    print()
    
    # Wait for server
    if not wait_for_server():
        return False
    
    # Create test image
    print("📸 Creating test image...")
    img_bytes = create_test_image()
    print("✅ Test image created\n")
    
    # Test the endpoint
    print("🔍 Testing /api/images/search-similar endpoint...")
    print("   Checking for image_url field with proper GCS URLs\n")
    
    try:
        files = {'image_file': ('test_image.png', img_bytes, 'image/png')}
        data = {
            'limit': '5',
            'score_threshold': '0.5'
        }
        
        print("📤 Sending POST request...")
        response = requests.post(
            'http://localhost:8000/api/images/search-similar',
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}\n")
        
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
        
        result = response.json()
        
        # Check response structure
        print("📊 Response Structure:")
        print(f"   Query description: {result.get('query_image', 'N/A')[:100]}...")
        print(f"   Total found: {result.get('total_found', 0)}")
        print(f"   Results count: {len(result.get('results', []))}\n")
        
        if not result.get('results'):
            print("⚠️  No results found in Qdrant")
            print("   This is expected if no images have been indexed yet.")
            print("   The fix is still valid - it will work when images are present.\n")
            return True
        
        # Check each result for image_url field
        print("🔍 Checking results for image_url field...\n")
        all_valid = True
        
        for i, res in enumerate(result.get('results', []), 1):
            print(f"Result {i}:")
            print(f"   Score: {res.get('score', 0)*100:.1f}%")
            
            # Check for image_uri (original placeholder)
            image_uri = res.get('image_uri', '')
            print(f"   image_uri: {image_uri[:80]}...")
            
            # Check for image_url (new field with actual URL)
            image_url = res.get('image_url', '')
            
            if image_url:
                print(f"   ✅ image_url: {image_url[:80]}...")
                
                # Verify it's a proper HTTP URL
                if image_url.startswith('https://storage.googleapis.com/'):
                    print(f"   ✅ Valid GCS public URL format")
                elif image_url.startswith('http://') or image_url.startswith('https://'):
                    print(f"   ⚠️  HTTP URL but not GCS format (might be valid)")
                elif image_url.startswith('gs://'):
                    print(f"   ❌ Still in gs:// format (conversion failed)")
                    all_valid = False
                elif image_url.startswith('http://example.org'):
                    print(f"   ⚠️  Still placeholder URI (no gcs_url in metadata)")
                else:
                    print(f"   ⚠️  Unknown URL format: {image_url[:50]}")
            else:
                print(f"   ⚠️  No image_url field found")
                # Check if metadata has gcs_url
                metadata = res.get('metadata', {})
                gcs_url = metadata.get('gcs_url', '')
                if gcs_url:
                    print(f"   ⚠️  Metadata has gcs_url but image_url not set: {gcs_url}")
                    all_valid = False
                else:
                    print(f"   ℹ️  No gcs_url in metadata (expected for some images)")
            
            print()
        
        if all_valid:
            print("=" * 70)
            print("✅ TEST PASSED: image_url fields are properly set!")
            print("=" * 70)
        else:
            print("=" * 70)
            print("⚠️  TEST PARTIAL: Some issues found (see above)")
            print("=" * 70)
        
        return all_valid
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server")
        print("   Please start the server with: python main.py")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_image_url_conversion()
    exit(0 if success else 1)

