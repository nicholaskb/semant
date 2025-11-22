#!/usr/bin/env python3
"""
Generate a REAL hot dog image using Midjourney
This will use the actual API if configured
"""
import asyncio
import os
from semant.agent_tools.midjourney.workflows import imagine_then_mirror

async def generate_real_hot_dog():
    """Generate a real hot dog image via Midjourney API"""
    
    print("🌭 GENERATING REAL HOT DOG IMAGE VIA MIDJOURNEY")
    print("=" * 60)
    
    # Check if we have API access
    if not os.getenv('MIDJOURNEY_API_TOKEN'):
        print("❌ No MIDJOURNEY_API_TOKEN found")
        print("To generate real images, set: export MIDJOURNEY_API_TOKEN='your-token'")
        return None
    
    print("✅ API Token found - proceeding with REAL generation")
    
    # Generate a hot dog image
    result = await imagine_then_mirror(
        prompt="professional food photography of a gourmet hot dog with steam rising, golden brown bun, fresh toppings, sesame seeds, ketchup and mustard, appetizing, commercial quality, high detail, warm lighting --ar 1:1 --v 6",
        version="v6",
        aspect_ratio="1:1",
        process_mode="fast"
    )
    
    print("\n✅ REAL MIDJOURNEY IMAGE GENERATED!")
    print(f"Task ID: {result.get('task_id')}")
    print(f"Image URL: {result.get('image_url')}")
    print(f"GCS URL: {result.get('gcs_url')}")
    
    return result

if __name__ == "__main__":
    asyncio.run(generate_real_hot_dog())

