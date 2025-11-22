#!/usr/bin/env python3
"""
Test REAL Midjourney image generation
This properly loads from .env file
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

async def test_midjourney():
    """Test real Midjourney generation with proper .env loading"""
    
    print("🎯 REAL MIDJOURNEY TEST")
    print("=" * 60)
    
    # Check environment
    api_token = os.getenv('MIDJOURNEY_API_TOKEN')
    gcs_bucket = os.getenv('GCS_BUCKET_NAME', 'bahroo_public')
    
    if not api_token or api_token == 'YOUR_ACTUAL_MIDJOURNEY_TOKEN_HERE':
        print("❌ MIDJOURNEY_API_TOKEN not configured in .env file")
        print("\n📝 To make this work:")
        print("1. Create a .env file in the project root")
        print("2. Add: MIDJOURNEY_API_TOKEN=your-actual-token")
        print("3. Get your token from GoAPI dashboard")
        print("\nExample .env file:")
        print("-" * 40)
        print("MIDJOURNEY_API_TOKEN=sk-xxxxx-your-actual-token-here")
        print("GCS_BUCKET_NAME=bahroo_public")
        print("-" * 40)
        return
    
    print(f"✅ API Token found: {api_token[:10]}...")
    print(f"✅ GCS Bucket: {gcs_bucket}")
    
    # Now test the actual Midjourney client
    from midjourney_integration.client import MidjourneyClient
    
    try:
        # Initialize the client
        client = MidjourneyClient(api_token=api_token)
        print("✅ MidjourneyClient initialized successfully")
        
        # Test with a simple imagine task
        print("\n🎨 Submitting hot dog image generation...")
        
        result = await client.submit_imagine(
            prompt="gourmet hot dog with melted cheese, crispy bacon, caramelized onions, on a toasted brioche bun, food photography, appetizing, warm lighting --ar 1:1 --v 6",
            model_version="v6",
            aspect_ratio="1:1",
            process_mode="fast"
        )
        
        if result:
            print(f"✅ Task submitted successfully!")
            print(f"   Task ID: {result.get('task_id')}")
            print(f"   Status: {result.get('status')}")
            
            # Save the task info
            task_dir = Path(f"midjourney_integration/jobs/{result['task_id']}")
            task_dir.mkdir(parents=True, exist_ok=True)
            
            with open(task_dir / "metadata.json", "w") as f:
                json.dump(result, f, indent=2)
            
            print(f"   Saved to: {task_dir}")
            
            # Poll for completion
            print("\n⏳ Polling for completion...")
            max_attempts = 60  # 5 minutes max
            for i in range(max_attempts):
                await asyncio.sleep(5)
                status = await client.poll_task(result['task_id'])
                
                if status.get('status') == 'completed':
                    print(f"✅ Image generation completed!")
                    print(f"   Image URL: {status.get('output', {}).get('image_url')}")
                    
                    # Download the image
                    import httpx
                    image_url = status['output']['image_url']
                    if image_url:
                        async with httpx.AsyncClient() as http_client:
                            response = await http_client.get(image_url)
                            if response.status_code == 200:
                                image_path = task_dir / "original.png"
                                with open(image_path, "wb") as f:
                                    f.write(response.content)
                                print(f"   Downloaded to: {image_path}")
                                print(f"\n🎉 SUCCESS! Real Midjourney image created!")
                                print(f"   Open with: open {image_path}")
                    break
                    
                elif status.get('status') == 'failed':
                    print(f"❌ Task failed: {status.get('error')}")
                    break
                    
                else:
                    print(f"   Status: {status.get('status')} ({i+1}/{max_attempts})")
        else:
            print("❌ Failed to submit task")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure .env file exists with valid MIDJOURNEY_API_TOKEN")
        print("2. Check that the API token is active on GoAPI")
        print("3. Ensure you have API credits available")

if __name__ == "__main__":
    # Install dotenv if needed
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Installing python-dotenv...")
        import subprocess
        subprocess.check_call(["pip", "install", "python-dotenv"])
        from dotenv import load_dotenv
    
    asyncio.run(test_midjourney())

