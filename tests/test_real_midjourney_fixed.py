#!/usr/bin/env python3
"""
Test REAL Midjourney image generation - FIXED VERSION
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

async def test_midjourney():
    """Test real Midjourney generation"""
    
    print("🎯 REAL MIDJOURNEY TEST - FIXED")
    print("=" * 60)
    
    api_token = os.getenv('MIDJOURNEY_API_TOKEN')
    if not api_token:
        print("❌ MIDJOURNEY_API_TOKEN not configured")
        return
    
    print(f"✅ API Token found: {api_token[:10]}...")
    
    from midjourney_integration.client import MidjourneyClient
    
    try:
        client = MidjourneyClient(api_token=api_token)
        print("✅ MidjourneyClient initialized")
        
        print("\n🎨 Submitting image generation...")
        
        result = await client.submit_imagine(
            prompt="gourmet hot dog with cheese and bacon, food photography --v 6",
            model_version="v6",
            aspect_ratio="1:1",
            process_mode="fast"
        )
        
        # Extract task_id from nested structure
        if result and result.get('data'):
            task_id = result['data'].get('task_id')
            status = result['data'].get('status')
            
            print(f"✅ Task submitted!")
            print(f"   Task ID: {task_id}")
            print(f"   Status: {status}")
            
            # Save metadata
            if task_id:
                task_dir = Path(f"midjourney_integration/jobs/{task_id}")
                task_dir.mkdir(parents=True, exist_ok=True)
                
                with open(task_dir / "metadata.json", "w") as f:
                    json.dump(result['data'], f, indent=2)
                
                print(f"   Saved to: {task_dir}")
                
                # Poll for completion
                print("\n⏳ Polling for completion...")
                for i in range(60):  # 5 minutes max
                    await asyncio.sleep(5)
                    
                    poll_result = await client.poll_task(task_id)
                    poll_data = poll_result.get('data', {})
                    current_status = poll_data.get('status')
                    
                    if current_status == 'completed':
                        output = poll_data.get('output', {})
                        image_url = output.get('image_url')
                        
                        print(f"✅ Image generation completed!")
                        print(f"   Image URL: {image_url}")
                        
                        if image_url:
                            # Download image
                            import httpx
                            async with httpx.AsyncClient() as http_client:
                                response = await http_client.get(image_url)
                                if response.status_code == 200:
                                    image_path = task_dir / "generated.png"
                                    with open(image_path, "wb") as f:
                                        f.write(response.content)
                                    print(f"   Downloaded to: {image_path}")
                                    print(f"\n🎉 SUCCESS!")
                                    print(f"   View: open {image_path}")
                        break
                        
                    elif current_status == 'failed':
                        error = poll_data.get('error', {})
                        print(f"❌ Task failed: {error.get('message', 'Unknown error')}")
                        break
                        
                    else:
                        progress = poll_data.get('output', {}).get('progress', 0)
                        print(f"   Status: {current_status} - Progress: {progress}% ({i+1}/60)")
                        
        else:
            print("❌ Unexpected response structure")
            print(f"Response: {result}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_midjourney())
