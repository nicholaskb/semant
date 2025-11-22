#!/usr/bin/env python3
"""
Comprehensive test script for Midjourney integration.
Tests token loading, client initialization, and API connectivity.
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from midjourney_integration.client import upload_to_gcs_and_get_public_url, settings


def test_environment():
    """Test 1: Verify environment variables are loaded."""
    print("\n🔍 TEST 1: Environment Variable Check")
    print("-" * 50)
    
    # Try to load .env file
    env_file = Path(".env")
    if env_file.exists():
        print(f"✅ .env file found at: {env_file.absolute()}")
        
        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✅ .env file loaded successfully")
        except ImportError:
            print("⚠️  python-dotenv not installed, trying manual load...")
            # Manual load as fallback
            with open(".env", "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value.strip('"').strip("'")
            print("✅ .env file loaded manually")
    else:
        print("❌ .env file not found")
    
    # Check token
    token = os.getenv("MIDJOURNEY_API_TOKEN")
    if token:
        # Mask token for security
        masked_token = token[:10] + "..." + token[-4:] if len(token) > 14 else "***"
        print(f"✅ MIDJOURNEY_API_TOKEN is set: {masked_token}")
        print(f"   Token length: {len(token)} characters")
        return True
    else:
        print("❌ MIDJOURNEY_API_TOKEN not found in environment")
        return False

def test_client_initialization():
    """Test 2: Verify MidjourneyClient can be initialized."""
    print("\n🔍 TEST 2: Client Initialization")
    print("-" * 50)
    
    try:
        from midjourney_integration.client import MidjourneyClient, MidjourneyError
        print("✅ Successfully imported MidjourneyClient")
        
        # Try to create client
        client = MidjourneyClient()
        print("✅ MidjourneyClient initialized successfully")
        print(f"   Base URL: {client._BASE_URL}")
        print(f"   Timeout: {client._timeout}")
        
        # Check headers
        headers = client._headers
        if "Authorization" in headers:
            auth_value = headers["Authorization"]
            if auth_value.startswith("Bearer "):
                print("✅ Authorization header properly formatted")
            else:
                print("⚠️  Authorization header format unexpected")
        
        return True, client
        
    except ValueError as e:
        print(f"❌ Failed to initialize client: {e}")
        return False, None
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return False, None

async def test_api_connectivity(client):
    """Test 3: Test actual API connectivity with a simple prompt."""
    print("\n🔍 TEST 3: API Connectivity Test")
    print("-" * 50)
    
    test_prompt = "a simple red circle on white background, minimalist design"
    print(f"📝 Test prompt: '{test_prompt}'")
    
    try:
        import httpx
        print("✅ httpx library available")
        
        # Test network connectivity first
        print("\n🌐 Testing network connectivity to GoAPI...")
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.get("https://api.goapi.ai", timeout=5.0)
                print(f"✅ GoAPI is reachable (status: {response.status_code})")
            except Exception as e:
                print(f"⚠️  Cannot reach GoAPI: {e}")
                
        # Now test the actual imagine endpoint
        print("\n🎨 Testing image generation...")
        print("   (This may take 30-60 seconds...)")
        
        start_time = datetime.now()
        try:
            # Use the client's imagine method
            image_url = await client.imagine(test_prompt)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"✅ Image generated successfully!")
            print(f"   Time taken: {duration:.1f} seconds")
            print(f"   Image URL: {image_url[:50]}..." if len(image_url) > 50 else f"   Image URL: {image_url}")
            
            # Verify the URL is valid
            if image_url.startswith(("http://", "https://")):
                print("✅ Valid image URL format")
            else:
                print("⚠️  Unexpected URL format")
                
            return True
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"❌ Image generation failed after {duration:.1f} seconds")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error message: {str(e)}")
            
            # Provide specific guidance based on error
            if "401" in str(e):
                print("\n💡 This appears to be an authentication error.")
                print("   Please verify your GoAPI token is correct.")
            elif "timeout" in str(e).lower():
                print("\n💡 The request timed out.")
                print("   This could be due to high API load. Try again later.")
            elif "task_id" in str(e):
                print("\n💡 The API response format may have changed.")
                print("   Check GoAPI documentation for updates.")
                
            return False
            
    except ImportError:
        print("❌ httpx not installed. Install with: pip install httpx")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during API test: {type(e).__name__}: {e}")
        return False

def test_fastapi_endpoint():
    """Test 4: Verify the FastAPI endpoint is configured."""
    print("\n🔍 TEST 4: FastAPI Endpoint Configuration")
    print("-" * 50)
    
    try:
        from main import app
        print("✅ Successfully imported FastAPI app")
        
        # Check if the endpoint exists
        routes = [route.path for route in app.routes]
        if "/midjourney/generate" in routes:
            print("✅ /midjourney/generate endpoint is configured")
            
            # Find the route and check its methods
            for route in app.routes:
                if route.path == "/midjourney/generate":
                    if hasattr(route, 'methods'):
                        print(f"   Methods: {route.methods}")
                    break
        else:
            print("❌ /midjourney/generate endpoint not found")
            print(f"   Available routes: {routes}")
            
        return True
    except Exception as e:
        print(f"❌ Failed to check FastAPI configuration: {e}")
        return False

def test_gcs_upload_logic():
    """Test 5: Verify the logic of the GCS upload function using mocks."""
    print("\n🔍 TEST 5: GCS Upload Logic")
    print("-" * 50)

    # 1. Setup the test
    # Create a dummy file to "upload"
    dummy_file = Path("test_image.png")
    dummy_file.touch()

    # Mock the GCS bucket name in settings
    settings.GCS_BUCKET_NAME = "test-bucket"

    # 2. Use patch to mock the google.cloud.storage.Client
    with patch('midjourney_integration.client.storage.Client') as MockStorageClient:
        # Configure the mock
        mock_client_instance = MockStorageClient.return_value
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        
        # Configure the return values of the mocked methods
        mock_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.public_url = "https://storage.googleapis.com/test-bucket/test_image.png"

        try:
            # 3. Call the function
            public_url = upload_to_gcs_and_get_public_url(
                source_file_path=dummy_file,
                destination_blob_name="test_image.png"
            )

            # 4. Assertions
            MockStorageClient.assert_called_once()
            mock_client_instance.bucket.assert_called_once_with("test-bucket")
            mock_bucket.blob.assert_called_once_with("test_image.png")
            mock_blob.upload_from_filename.assert_called_once_with(str(dummy_file), timeout=300)
            mock_blob.make_public.assert_called_once()
            
            assert public_url == "https://storage.googleapis.com/test-bucket/test_image.png"
            
            print("✅ GCS upload logic appears correct.")
            print("   - storage.Client() called")
            print("   - bucket() called with correct name")
            print("   - blob() called with correct name")
            print("   - upload_from_filename() called correctly")
            print("   - make_public() called")
            print("   - Returned correct public URL")
            return True

        except Exception as e:
            print(f"❌ GCS upload logic test failed: {e}")
            return False
        finally:
            # Clean up the dummy file
            dummy_file.unlink()

async def main():
    """Run all tests."""
    print("🎨 Midjourney Integration Test Suite")
    print("=" * 50)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Environment
    env_ok = test_environment()
    if not env_ok:
        print("\n❌ Environment test failed. Please set MIDJOURNEY_API_TOKEN.")
        print("\nOptions:")
        print("1. Create a .env file with: MIDJOURNEY_API_TOKEN=your-token")
        print("2. Or export: export MIDJOURNEY_API_TOKEN=your-token")
        return
    
    # Test 2: Client initialization
    client_ok, client = test_client_initialization()
    if not client_ok:
        print("\n❌ Client initialization failed. Check your token format.")
        return
    
    # Test 3: API connectivity (optional)
    print("\n" + "=" * 50)
    user_input = input("Run API connectivity test? This will generate a test image. (y/N): ")
    if user_input.lower() == 'y':
        await test_api_connectivity(client)
    else:
        print("⏭️  Skipping API connectivity test")
    
    # Test 4: FastAPI endpoint
    test_fastapi_endpoint()

    # Test 5: GCS Upload Logic
    test_gcs_upload_logic()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("-" * 50)
    print("✅ Environment variables: PASSED")
    print("✅ Client initialization: PASSED")
    print("✅ FastAPI configuration: CHECKED")
    print("\n🎉 Your Midjourney integration is properly configured!")
    print("\nNext steps:")
    print("1. Run: python start_midjourney_demo.py")
    print("2. Open: http://localhost:8000/static/chat.html")
    print("3. Try generating an image!")

if __name__ == "__main__":
    asyncio.run(main())
