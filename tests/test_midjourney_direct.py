#!/usr/bin/env python3
"""Quick test of Midjourney client."""

import asyncio
import os
from dotenv import load_dotenv
from midjourney_integration.client import MidjourneyClient

async def test():
    # Load environment
    load_dotenv()
    
    # Check token
    token = os.getenv("MIDJOURNEY_API_TOKEN")
    if not token:
        print("ERROR: MIDJOURNEY_API_TOKEN not found in environment")
        return
        
    print(f"Token found: {token[:10]}...")
    
    # Test client
    try:
        client = MidjourneyClient()
        
        # Try a simple imagine
        response = await client.submit_imagine(
            prompt="A simple test image, watercolor style",
            aspect_ratio="16:9",
            model_version="V_6",
            process_mode="relax"
        )
        
        print(f"Response: {response}")
        
        if isinstance(response, dict) and "data" in response:
            task_id = response["data"].get("task_id")
            print(f"Task ID: {task_id}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())

