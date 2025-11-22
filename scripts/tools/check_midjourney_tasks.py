#!/usr/bin/env python3
"""
Check status of Midjourney tasks and retrieve completed images
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

async def check_task_status(task_id: str):
    """Check the status of a specific Midjourney task."""
    from midjourney_integration.client import MidjourneyClient
    
    try:
        client = MidjourneyClient()
        
        # Get task status
        result = await client.poll_task(task_id)
        
        if isinstance(result, dict):
            if "data" in result:
                data = result["data"]
            else:
                data = result
            
            status = data.get("status", "unknown")
            progress = data.get("progress", 0)
            
            print(f"Task {task_id[:8]}...")
            print(f"  Status: {status}")
            print(f"  Progress: {progress}%")
            
            if status == "completed":
                output = data.get("output", {})
                image_url = (output.get("image_url") or 
                           output.get("url") or
                           output.get("discord_image_url"))
                if image_url:
                    print(f"  ✅ Image URL: {image_url[:50]}...")
                    return {"task_id": task_id, "status": "completed", "image_url": image_url}
            
            return {"task_id": task_id, "status": status, "progress": progress}
            
    except Exception as e:
        print(f"Error checking task {task_id}: {e}")
        return {"task_id": task_id, "status": "error", "error": str(e)}


async def check_all_recent_tasks():
    """Check all tasks from the recent book generation attempts."""
    
    # Tasks from the recent run
    task_ids = [
        "4dbb7b7d-6bb5-40dc-8c17-f16a7d53609e",  # Page 1: Meet Quacky
        "bb412386-b38b-46b9-9a59-7bc12e718f54",  # Page 3: Too Big Feet
        "1ecadbf5-2d85-4bd0-b832-fd09beb29ae4",  # Page 5: Meeting Freddy
        "83af08bb-4d5d-4538-9999-072e476bc980",  # Page 7: Waddle Hop
        "0d4596f5-8fe4-470d-92ab-580682b14255",  # Page 9: Wise Goose
        "ed8725a6-0265-4936-875f-b7d048ab1926",  # Page 12: Happy Ending
    ]
    
    page_titles = {
        "4dbb7b7d-6bb5-40dc-8c17-f16a7d53609e": "Page 1: Meet Quacky",
        "bb412386-b38b-46b9-9a59-7bc12e718f54": "Page 3: Too Big Feet",
        "1ecadbf5-2d85-4bd0-b832-fd09beb29ae4": "Page 5: Meeting Freddy",
        "83af08bb-4d5d-4538-9999-072e476bc980": "Page 7: Waddle Hop",
        "0d4596f5-8fe4-470d-92ab-580682b14255": "Page 9: Wise Goose",
        "ed8725a6-0265-4936-875f-b7d048ab1926": "Page 12: Happy Ending",
    }
    
    print("🔍 Checking Midjourney Task Status...")
    print("=" * 60)
    
    results = []
    completed_count = 0
    
    for task_id in task_ids:
        title = page_titles.get(task_id, "Unknown")
        print(f"\n{title}")
        
        result = await check_task_status(task_id)
        results.append(result)
        
        if result["status"] == "completed":
            completed_count += 1
        
        await asyncio.sleep(1)  # Rate limiting
    
    print("\n" + "=" * 60)
    print(f"✨ Summary: {completed_count}/{len(task_ids)} tasks completed")
    
    # Save results
    output_dir = Path("quacky_book_output/task_status")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = output_dir / f"status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump({
            "checked_at": datetime.now().isoformat(),
            "tasks": results,
            "completed": completed_count,
            "total": len(task_ids)
        }, f, indent=2)
    
    print(f"\n📁 Results saved to: {results_file}")
    
    # If all completed, create a final book with images
    if completed_count == len(task_ids):
        print("\n🎉 All tasks completed! You can now generate the final book with images.")
        
        # Save image URLs for easy access
        images_file = output_dir / "completed_images.json"
        completed_images = {
            page_titles[r["task_id"]]: r["image_url"] 
            for r in results if r["status"] == "completed"
        }
        
        with open(images_file, "w") as f:
            json.dump(completed_images, f, indent=2)
        
        print(f"📸 Image URLs saved to: {images_file}")
    
    return results


if __name__ == "__main__":
    asyncio.run(check_all_recent_tasks())
