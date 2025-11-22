#!/usr/bin/env python3
"""
WORKING Children's Book Generator - Simplified and Robust
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv()

class SimpleBookGenerator:
    """Dead simple book generator that actually works."""
    
    def __init__(self):
        self.workflow_id = f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = Path(f"final_book/{self.workflow_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.book_content = {
            1: {"title": "Meet Quacky", "text": "Down by the pond lived Quacky McWaddles with the BIGGEST orange feet!"},
            2: {"title": "Super Splash", "text": "Watch me do my SUPER SPLASH! *KER-SPLASH!* Oopsie, belly-flop!"},
            3: {"title": "Big Feet Problem", "text": "My feet are ENORMOUS! The other ducklings giggled."},
            4: {"title": "Finding Help", "text": "I'll find the Wise Old Goose! She'll know what to do!"},
            5: {"title": "Meeting Friends", "text": "Are you wearing FLIPPERS? asked Freddy Frog."},
            6: {"title": "Getting Tangled", "text": "Oh no! His feet got tangled in the grass!"},
            7: {"title": "The Waddle Hop", "text": "If I can't walk, I'll HOP! *BOING BOING!*"},
            8: {"title": "More Dancing", "text": "The bunnies loved the new Waddle Hop dance!"},
            9: {"title": "Wise Advice", "text": "Your big feet are SUPERPOWERS for swimming!"},
            10: {"title": "Racing Back", "text": "Quacky WADDLE-HOPPED back. Who wants to RACE?"},
            11: {"title": "Victory!", "text": "Quacky's big feet made him ZOOM through the water!"},
            12: {"title": "Happy Ending", "text": "Being different is QUACK-A-DOODLE-AWESOME!"}
        }
        
    async def generate_single_image(self, prompt: str, page_num: int):
        """Generate ONE image that actually works."""
        from midjourney_integration.client import MidjourneyClient, poll_until_complete
        
        print(f"\n📸 Generating Page {page_num}...")
        
        try:
            client = MidjourneyClient()
            
            # Super simple prompt - no fancy parameters
            simple_prompt = prompt.replace("--ar 16:9", "").replace("--v 6", "").strip()
            
            # Submit with minimal parameters
            response = await client.submit_imagine(
                prompt=simple_prompt,
                aspect_ratio="16:9",
                process_mode="relax",
                model_version=None  # Let it use default
            )
            
            # Get task ID
            task_id = None
            if isinstance(response, dict):
                task_id = response.get("data", {}).get("task_id") or response.get("task_id")
            
            if not task_id:
                print(f"❌ No task_id received")
                return None
                
            print(f"✅ Task submitted: {task_id}")
            
            # Wait longer with more patience
            print("⏳ Waiting for generation (this may take 5-10 minutes)...")
            
            # Try multiple times to get the result
            for attempt in range(3):
                try:
                    result = await poll_until_complete(client, task_id, interval=10, max_wait=300)
                    
                    # Extract image URL
                    if isinstance(result, dict):
                        output = result.get("output", {})
                        image_url = (output.get("image_url") or 
                                   output.get("url") or
                                   output.get("discord_image_url"))
                        
                        if image_url:
                            print(f"✅ SUCCESS! Image URL: {image_url[:60]}...")
                            return {
                                "page": page_num,
                                "task_id": task_id,
                                "image_url": image_url,
                                "timestamp": datetime.now().isoformat()
                            }
                except TimeoutError:
                    print(f"⏳ Attempt {attempt + 1} timed out, checking status...")
                    
                    # Check status directly
                    status_result = await client.poll_task(task_id)
                    status_data = status_result.get("data", status_result)
                    status = status_data.get("status", "unknown")
                    
                    print(f"   Status: {status}")
                    
                    if status == "completed":
                        output = status_data.get("output", {})
                        image_url = (output.get("image_url") or 
                                   output.get("url") or
                                   output.get("discord_image_url"))
                        if image_url:
                            print(f"✅ Found completed image: {image_url[:60]}...")
                            return {
                                "page": page_num,
                                "task_id": task_id,
                                "image_url": image_url,
                                "timestamp": datetime.now().isoformat()
                            }
                    
                    await asyncio.sleep(30)  # Wait more between attempts
            
            print(f"❌ Could not get image after all attempts")
            return None
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def create_book_html(self, images: dict):
        """Create a beautiful HTML book."""
        
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Quacky McWaddles' Big Adventure</title>
    <style>
        body {
            font-family: 'Comic Sans MS', cursive;
            background: linear-gradient(to bottom, #87CEEB, #98FB98);
            padding: 20px;
            margin: 0;
        }
        .book-title {
            text-align: center;
            font-size: 48px;
            color: #FF6B35;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.2);
            margin: 30px 0;
        }
        .page {
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin: 20px auto;
            max-width: 800px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .page-number {
            color: #4A90E2;
            font-size: 18px;
            font-weight: bold;
        }
        .page-title {
            font-size: 32px;
            color: #FF6B35;
            margin: 10px 0;
        }
        .page-text {
            font-size: 24px;
            line-height: 1.6;
            color: #333;
            margin: 20px 0;
        }
        .page-image {
            width: 100%;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            margin: 20px 0;
        }
        .no-image {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 400px;
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
        }
        .footer {
            text-align: center;
            margin-top: 50px;
            font-size: 28px;
            color: #FF6B35;
            font-weight: bold;
        }
        .interactive {
            background: #FFE66D;
            padding: 15px;
            border-radius: 10px;
            font-size: 20px;
            margin: 15px 0;
            text-align: center;
        }
    </style>
</head>
<body>
    <h1 class="book-title">🦆 Quacky McWaddles' Big Adventure 🦆</h1>
"""
        
        for page_num in range(1, 13):
            content = self.book_content[page_num]
            html += f"""
    <div class="page">
        <div class="page-number">Page {page_num}</div>
        <h2 class="page-title">{content['title']}</h2>
        <div class="page-text">{content['text']}</div>
"""
            
            if page_num in images:
                img = images[page_num]
                html += f'        <img src="{img["image_url"]}" alt="Page {page_num}" class="page-image">\n'
            else:
                html += f'        <div class="no-image">🎨 Illustration Coming Soon!</div>\n'
            
            # Add interactive elements
            if page_num == 1:
                html += '        <div class="interactive">🦆 Can YOU make a splash sound? SPLASH!</div>\n'
            elif page_num == 7:
                html += '        <div class="interactive">🦆 Try the Waddle Hop! BOING BOING!</div>\n'
            elif page_num == 12:
                html += '        <div class="interactive">🦆 What makes YOU special?</div>\n'
            
            html += '    </div>\n'
        
        html += """
    <div class="footer">
        The End! Remember: Being different makes you QUACK-A-DOODLE-AWESOME! 🦆
    </div>
</body>
</html>"""
        
        return html
    
    async def run(self):
        """Generate the book with whatever images we can get."""
        
        print("\n" + "="*60)
        print("📚 QUACKY MCWADDLES BOOK GENERATOR")
        print("="*60)
        
        # We already have one working image from the check!
        existing_images = {
            1: {
                "page": 1,
                "task_id": "4dbb7b7d-6bb5-40dc-8c17-f16a7d53609e",
                "image_url": "https://cdn.discordapp.com/attachments/1417462350976532534/1287834765250789477/bahroo_cute_yellow_duckling_with_huge_orange_webbed_feet_by_a_5b2dc7ba-c436-440f-a42c-c962e9df7c05.png",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        print("\n✅ Using existing completed image for Page 1")
        
        # Try to generate just 2 more key images
        prompts = [
            (7, "happy yellow duckling hopping and dancing"),  # Waddle Hop
            (12, "yellow duckling celebrating with friends by pond")  # Happy Ending
        ]
        
        print("\n🎨 Generating 2 additional key illustrations...")
        print("(Using simple prompts for better success)\n")
        
        generated = {}
        for page_num, prompt in prompts:
            result = await self.generate_single_image(prompt, page_num)
            if result:
                generated[page_num] = result
            await asyncio.sleep(5)  # Be nice to the API
        
        # Combine all images
        all_images = {**existing_images, **generated}
        
        print(f"\n📊 Total illustrations: {len(all_images)}/12")
        
        # Create the book files
        print("\n📖 Creating book files...")
        
        # Save as HTML
        html_content = self.create_book_html(all_images)
        html_path = self.output_dir / "quacky_book.html"
        html_path.write_text(html_content)
        print(f"✅ HTML book: {html_path}")
        
        # Save metadata
        meta_path = self.output_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump({
                "title": "Quacky McWaddles' Big Adventure",
                "workflow_id": self.workflow_id,
                "created_at": datetime.now().isoformat(),
                "illustrations": all_images,
                "total_pages": 12,
                "pages_with_images": len(all_images)
            }, f, indent=2)
        print(f"✅ Metadata: {meta_path}")
        
        # Create markdown version too
        md_content = "# Quacky McWaddles' Big Adventure\n\n"
        for page_num in range(1, 13):
            content = self.book_content[page_num]
            md_content += f"## Page {page_num}: {content['title']}\n\n"
            if page_num in all_images:
                md_content += f"![Page {page_num}]({all_images[page_num]['image_url']})\n\n"
            md_content += f"{content['text']}\n\n---\n\n"
        
        md_path = self.output_dir / "quacky_book.md"
        md_path.write_text(md_content)
        print(f"✅ Markdown: {md_path}")
        
        print("\n" + "="*60)
        print("✨ BOOK GENERATION COMPLETE!")
        print(f"📁 Output: {self.output_dir}")
        print(f"🌐 Open {html_path.name} in a browser to view!")
        print("="*60 + "\n")
        
        return True


async def main():
    """Simple main function."""
    if not os.getenv("MIDJOURNEY_API_TOKEN"):
        print("❌ Missing MIDJOURNEY_API_TOKEN")
        return
    
    generator = SimpleBookGenerator()
    await generator.run()


if __name__ == "__main__":
    asyncio.run(main())
