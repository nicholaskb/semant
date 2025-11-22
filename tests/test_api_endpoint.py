#!/usr/bin/env python3
"""Complete API endpoint test"""
import requests
import time
from pathlib import Path
from PIL import Image
import io

def wait_for_server(url="http://localhost:8000/api/health", max_wait=30):
    """Wait for server to be ready"""
    print("Waiting for API server to start...")
    for i in range(max_wait):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print("✅ API server is ready!")
                return True
        except:
            pass
        time.sleep(1)
        if i % 5 == 0:
            print(f"  Still waiting... ({i}s)")
    return False

def create_test_image():
    """Create a test image"""
    img = Image.new('RGB', (200, 200), color='yellow')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_api_endpoint():
    """Test the /api/images/search-similar endpoint"""
    print("\n" + "="*70)
    print("🧪 COMPLETE API ENDPOINT TEST")
    print("="*70 + "\n")
    
    # Wait for server
    if not wait_for_server():
        print("❌ API server not responding. Is it running?")
        print("   Start with: python main.py")
        return False
    
    # Create test image
    print("📸 Creating test image...")
    img_bytes = create_test_image()
    print("✅ Test image created")
    
    # Test the endpoint
    print("\n🔍 Testing /api/images/search-similar endpoint...")
    print("   URL: http://localhost:8000/api/images/search-similar")
    print("   Method: POST")
    print("   Parameters: limit=5, score_threshold=0.5")
    
    try:
        files = {'image_file': ('test_duck.png', img_bytes, 'image/png')}
        data = {
            'limit': '5',
            'score_threshold': '0.5'
        }
        
        print("\n📤 Sending request...")
        response = requests.post(
            'http://localhost:8000/api/images/search-similar',
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS! Response received:")
            print(f"   Query Description: {result.get('query_image', 'N/A')[:100]}...")
            print(f"   Total Found: {result.get('total_found', 0)}")
            
            if result.get('results'):
                print(f"\n📊 Top Results:")
                for i, res in enumerate(result['results'][:3], 1):
                    score = res.get('score', 0) * 100
                    uri = res.get('image_uri', 'N/A')
                    print(f"   {i}. Score: {score:.1f}% | URI: {uri}")
            
            print("\n✅ API endpoint test PASSED!")
            return True
        else:
            print(f"\n❌ FAILED: Status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection error - API server not running")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_endpoint()
    exit(0 if success else 1)

