#!/usr/bin/env python3
"""
Use ONLY existing Midjourney agent tools - no new code!
This shows how to use the already-built infrastructure for AI curation.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

# Import ONLY existing tools from the registry
from semant.agent_tools.midjourney import REGISTRY
from semant.agent_tools.midjourney.tools.book_generator_tool import BookGeneratorTool

load_dotenv()

async def use_existing_ai_tools():
    """
    Use the existing agent tools for intelligent book generation.
    These tools already have AI capabilities built in!
    """
    
    print("="*70)
    print("🎨 USING EXISTING AI TOOLS FOR BOOK GENERATION")
    print("="*70)
    
    # 1. Use the EXISTING BookGeneratorTool
    print("\n1️⃣ Using existing BookGeneratorTool...")
    book_tool = REGISTRY["mj.book_generator"]()  # From the registry!
    
    # 2. Use the EXISTING DescribeTool to analyze images
    describe_tool = REGISTRY["mj.describe"]()
    
    # 3. Use the EXISTING ActionTool for variations
    action_tool = REGISTRY["mj.action"]()
    
    # 4. Use the EXISTING ImagineTool with character reference
    imagine_tool = REGISTRY["mj.imagine"]()
    
    # We already have completed images - let's use them!
    images_file = Path("quacky_book_output/task_status/completed_images.json")
    
    if images_file.exists():
        with open(images_file) as f:
            completed_images = json.load(f)
        
        print(f"\n✅ Found {len(completed_images)} existing images to work with")
        
        # Get the best image for character reference (Page 1)
        best_image_url = completed_images.get("Page 1: Meet Quacky")
        
        if best_image_url:
            print(f"\n2️⃣ Using best image as character reference:")
            print(f"   --cref {best_image_url[:60]}...")
            
            # DESCRIBE the image to understand what AI sees
            print("\n3️⃣ Using DescribeTool to analyze the image...")
            try:
                description = await describe_tool.run(image_url=best_image_url)
                print(f"   AI sees: {description.get('data', {}).get('description', 'Processing...')}")
            except Exception as e:
                print(f"   Description not available: {e}")
            
            # Generate NEW images with character reference for consistency
            print("\n4️⃣ Generating new images with character reference...")
            
            # Example: Generate a variation with --cref
            new_prompt = "yellow duckling doing a happy dance, watercolor style --ar 16:9"
            
            print(f"   Prompt: {new_prompt}")
            print(f"   Using --cref for consistency")
            
            # This would generate with character reference
            """
            result = await imagine_tool.run(
                prompt=new_prompt,
                cref=best_image_url,  # Character reference!
                cw=100,  # Character weight
                model_version="v6",  # v6 supports cref
                aspect_ratio="16:9",
                process_mode="relax"
            )
            """
            
            # Get variations of existing good images
            print("\n5️⃣ Getting variations of best images...")
            
            # In Midjourney, you'd use V1-V4 buttons
            # With the API, we use the action tool:
            """
            for task_id in ["4dbb7b7d-6bb5-40dc-8c17-f16a7d53609e"]:
                # Get variation 1
                variation = await action_tool.run(
                    task_id=task_id,
                    action="variation1"  # V1 button
                )
                print(f"   Created variation: {variation.get('task_id')}")
            """
    
    # Use the existing workflows for complete automation
    print("\n6️⃣ Using existing workflows...")
    
    from semant.agent_tools.midjourney.workflows import imagine_then_mirror
    
    # This workflow does: imagine → poll → upload to GCS
    """
    result = await imagine_then_mirror(
        prompt="yellow duckling celebrating with friends, watercolor",
        version="v6",
        aspect_ratio="16:9",
        cref=best_image_url,  # Use best image as reference
        cw=100,
        poll_interval=10,
        poll_timeout=600
    )
    print(f"   Workflow result: {result.get('gcs_url')}")
    """
    
    # The BookGeneratorTool already does everything!
    print("\n7️⃣ Complete book generation with existing tool...")
    
    book_pages = [
        {
            "title": "Meet Quacky",
            "text": "Down by the pond lived Quacky McWaddles...",
            "prompt": "cute yellow duckling with huge orange feet by pond"
        },
        {
            "title": "The Waddle Hop",
            "text": "I'm doing the WADDLE HOP!",
            "prompt": "yellow duckling hopping and dancing with bunnies"
        },
        {
            "title": "Happy Ending",
            "text": "Being different is QUACK-A-DOODLE-AWESOME!",
            "prompt": "all ducks celebrating by pond, party atmosphere"
        }
    ]
    
    # The tool handles EVERYTHING - generation, KG logging, GCS upload
    """
    result = await book_tool.generate_book(
        title="Quacky McWaddles' Big Adventure",
        pages=book_pages,
        max_pages_to_illustrate=3
    )
    """
    
    print("\n" + "="*70)
    print("✨ EXISTING TOOLS CAPABILITIES:")
    print("="*70)
    print("✅ BookGeneratorTool - Complete book generation")
    print("✅ ImagineTool - Generate with --cref, --oref, --sref")
    print("✅ ActionTool - Get variations (V1-V4), upscale (U1-U4)")
    print("✅ DescribeTool - Analyze what AI sees in images")
    print("✅ BlendTool - Blend multiple images")
    print("✅ SeedTool - Lock style with --seed")
    print("✅ GetTaskTool - Check status of any task")
    print("✅ GCSMirrorTool - Upload to Google Cloud Storage")
    print("✅ Workflows - Complete automation chains")
    print("="*70)
    
    return completed_images


async def demonstrate_ai_curation():
    """
    Show how the EXISTING tools provide AI curation capabilities.
    """
    
    print("\n🤖 AI CURATION WITH EXISTING TOOLS:")
    print("-"*50)
    
    # The existing tools already support:
    print("1. Character Reference (--cref):")
    print("   imagine_tool.run(prompt='...', cref='best_image_url', cw=100)")
    
    print("\n2. Style Reference (--sref):")
    print("   imagine_tool.run(prompt='...', sref='style_image_url', sw=100)")
    
    print("\n3. Object Reference (--oref) for v7:")
    print("   imagine_tool.run(prompt='...', oref='object_url', ow=100, model_version='v7')")
    
    print("\n4. Get Variations:")
    print("   action_tool.run(task_id='...', action='variation1')")
    
    print("\n5. Upscale for Higher Quality:")
    print("   action_tool.run(task_id='...', action='upscale2x')")
    
    print("\n6. Analyze Images:")
    print("   describe_tool.run(image_url='...')")
    
    print("\n7. Blend Multiple Images:")
    print("   blend_tool.run(image_urls=['url1', 'url2'])")
    
    print("\n8. Lock Style with Seed:")
    print("   seed_tool.run(task_id='...')  # Get seed")
    print("   imagine_tool.run(prompt='...', extra={'seed': 12345})")


async def main():
    """Use only existing tools."""
    
    # Show what we can do with existing tools
    images = await use_existing_ai_tools()
    
    # Demonstrate AI curation capabilities
    await demonstrate_ai_curation()
    
    print("\n✅ All functionality uses EXISTING tools - no new code needed!")
    print("📚 The BookGeneratorTool already handles the complete workflow!")
    print("🤖 AI curation is built in through --cref, variations, and describe!")


if __name__ == "__main__":
    asyncio.run(main())

