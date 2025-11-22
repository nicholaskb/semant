#!/usr/bin/env python3
"""
Debug the Midjourney API connection
"""

import asyncio
import os
from dotenv import load_dotenv
from midjourney_integration.client import MidjourneyClient

async def test_submit():
    """Test the submit_imagine method directly."""
    
    # Load environment
    load_dotenv()
    
    token = os.getenv("MIDJOURNEY_API_TOKEN")
    if not token:
        print("❌ No MIDJOURNEY_API_TOKEN found in environment")
        return
    
    print(f"✅ Token found: {token[:10]}...")
    
    # Create client
    try:
        client = MidjourneyClient()
        print("✅ Client created successfully")
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        return
    
    # Test simple prompt
    prompt = "A simple test: red circle on white background --v 6"
    
    print(f"\n📝 Testing with prompt: {prompt}")
    
    try:
        # Submit the request
        result = await client.submit_imagine(
            prompt=prompt,
            aspect_ratio="1:1",
            process_mode="relax",
            model_version="V_6"
        )
        
        print("\n📦 Raw response:")
        import json
        print(json.dumps(result, indent=2))
        
        # Check for task_id
        task_id = result.get("task_id") or result.get("data", {}).get("task_id")
        
        if task_id:
            print(f"\n✅ Got task_id: {task_id}")
        else:
            print(f"\n❌ No task_id in response")
            
            # Check for errors
            if "error" in result:
                print(f"Error in response: {result['error']}")
            if "message" in result:
                print(f"Message: {result['message']}")
                
    except Exception as e:
        print(f"\n❌ Failed to submit: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_submit())

