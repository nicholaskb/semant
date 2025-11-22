#!/usr/bin/env python3
"""
Create a REAL Hot Dog Flier with actual Midjourney images
This properly uses .env file for credentials
"""
import asyncio
import os
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class RealHotDogFlier:
    """Create a hot dog flier with REAL Midjourney images"""
    
    def __init__(self):
        self.api_token = os.getenv('MIDJOURNEY_API_TOKEN')
        self.output_dir = Path("midjourney_integration/jobs/real-hot-dog-flier")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def generate_images(self):
        """Generate real Midjourney images for the flier"""
        from midjourney_integration.client import MidjourneyClient
        
        if not self.api_token or self.api_token == 'YOUR_ACTUAL_MIDJOURNEY_TOKEN_HERE':
            print("❌ No valid MIDJOURNEY_API_TOKEN in .env")
            print("\n📝 Please create .env file with:")
            print("MIDJOURNEY_API_TOKEN=your-actual-token")
            return None
        
        client = MidjourneyClient(api_token=self.api_token)
        print("✅ MidjourneyClient initialized with token from .env")
        
        # Define our hot dog images
        prompts = [
            {
                "name": "hero_hotdog",
                "prompt": "gourmet Chicago-style hot dog, professional food photography, steam rising, golden brown bun with sesame seeds, bright green relish, yellow mustard, white onions, tomato slices, pickle spear, sport peppers, celery salt, appetizing, commercial quality, warm lighting, shallow depth of field --ar 1:1 --v 6",
            },
            {
                "name": "classic_hotdog",
                "prompt": "classic American hot dog with ketchup and mustard, grilled to perfection, toasted bun, professional food photography, appetizing presentation, warm golden hour lighting, detailed texture, commercial quality --ar 1:1 --v 6",
            },
            {
                "name": "loaded_hotdog",
                "prompt": "loaded chili cheese hot dog, melted cheddar, meat chili, crispy bacon bits, green onions, sour cream dollop, professional food photography, indulgent, appetizing, dramatic lighting, steam rising --ar 1:1 --v 6",
            }
        ]
        
        generated_images = []
        
        for i, spec in enumerate(prompts, 1):
            print(f"\n🌭 Generating image {i}/3: {spec['name']}")
            print(f"   Prompt: {spec['prompt'][:80]}...")
            
            try:
                # Submit the imagine task
                result = await client.submit_imagine(
                    prompt=spec['prompt'],
                    version="v6",
                    aspect_ratio="1:1",
                    process_mode="fast"
                )
                
                if result and result.get('task_id'):
                    task_id = result['task_id']
                    print(f"   ✅ Task submitted: {task_id}")
                    
                    # Poll for completion (max 5 minutes)
                    for attempt in range(60):
                        await asyncio.sleep(5)
                        status = await client.get_task(task_id)
                        
                        if status.get('status') == 'completed':
                            image_url = status.get('output', {}).get('image_url')
                            if image_url:
                                print(f"   ✅ Image ready: {image_url}")
                                
                                # Download the image
                                import httpx
                                async with httpx.AsyncClient() as http:
                                    response = await http.get(image_url)
                                    if response.status_code == 200:
                                        image_path = self.output_dir / f"{spec['name']}.png"
                                        with open(image_path, "wb") as f:
                                            f.write(response.content)
                                        
                                        generated_images.append({
                                            "name": spec['name'],
                                            "path": str(image_path),
                                            "task_id": task_id,
                                            "url": image_url
                                        })
                                        print(f"   ✅ Downloaded to: {image_path}")
                                        break
                        
                        elif status.get('status') == 'failed':
                            print(f"   ❌ Failed: {status.get('error')}")
                            break
                        
                        else:
                            if attempt % 6 == 0:  # Update every 30 seconds
                                print(f"   ⏳ Status: {status.get('status')} ({attempt*5}s elapsed)")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        return generated_images
    
    def create_flier(self, images):
        """Create the flier with the generated images"""
        print("\n📋 Creating flier composition...")
        
        # Create flier canvas
        flier = Image.new('RGB', (800, 1200), color='#FFF8DC')  # Cornsilk background
        draw = ImageDraw.Draw(flier)
        
        # Try to use a nice font, fall back to default
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
        
        # Add title
        draw.text((400, 50), "🌭 HOT DOG FEST 2025! 🌭", 
                 font=title_font, anchor="mt", fill='#8B0000')
        
        draw.text((400, 110), "The Ultimate Gourmet Experience", 
                 font=subtitle_font, anchor="mt", fill='#FF6347')
        
        # Add images if we have them
        y_pos = 180
        for i, img_info in enumerate(images[:3]):  # Use up to 3 images
            if os.path.exists(img_info['path']):
                try:
                    img = Image.open(img_info['path'])
                    # Resize to fit
                    img.thumbnail((220, 220), Image.Resampling.LANCZOS)
                    # Position images in a row
                    x_pos = 100 + (i * 250)
                    flier.paste(img, (x_pos, y_pos))
                    print(f"   ✅ Added {img_info['name']} to flier")
                except Exception as e:
                    print(f"   ⚠️ Could not add {img_info['name']}: {e}")
        
        # Add event details
        y_pos = 450
        details = [
            "📅 Saturday, July 4th, 2025",
            "📍 Central Park, Downtown",
            "⏰ 11 AM - 8 PM",
            "",
            "🎯 FEATURING:",
            "• Chicago Style Dogs",
            "• Loaded Chili Cheese Dogs", 
            "• Gourmet Artisan Creations",
            "• Vegan & Veggie Options",
            "",
            "🎵 Live Music | 🎪 Kids Zone | 🍺 Craft Beer",
            "",
            "Tickets: $15 Adults | $8 Kids | Under 5 FREE",
            "🎟️ Get tickets at: hotdogfest2025.com"
        ]
        
        for line in details:
            if line.startswith("🎯"):
                draw.text((400, y_pos), line, font=subtitle_font, anchor="mt", fill='#8B0000')
            else:
                draw.text((400, y_pos), line, font=body_font, anchor="mt", fill='#333333')
            y_pos += 35 if line == "" else 40
        
        # Add footer
        draw.rectangle([(0, 1100), (800, 1200)], fill='#8B0000')
        draw.text((400, 1150), "Made with REAL Midjourney Images", 
                 font=body_font, anchor="mm", fill='white')
        
        # Save the flier
        flier_path = self.output_dir / "hot_dog_flier.png"
        flier.save(flier_path, quality=95)
        print(f"\n✅ Flier saved to: {flier_path}")
        
        return str(flier_path)
    
    async def run(self):
        """Main workflow"""
        print("🌭 CREATING REAL HOT DOG FLIER WITH MIDJOURNEY")
        print("=" * 60)
        
        # Generate real images
        images = await self.generate_images()
        
        if not images:
            print("\n❌ No images generated. Please configure .env file:")
            print("1. Create .env file in project root")
            print("2. Add: MIDJOURNEY_API_TOKEN=your-actual-token")
            print("3. Get token from: https://www.theapi.app/")
            return
        
        print(f"\n✅ Generated {len(images)} real Midjourney images!")
        
        # Create the flier
        flier_path = self.create_flier(images)
        
        # Save metadata
        metadata = {
            "created_at": datetime.now().isoformat(),
            "images": images,
            "flier_path": flier_path,
            "used_real_midjourney": True,
            "api_token_source": ".env file"
        }
        
        with open(self.output_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        print("\n" + "=" * 60)
        print("🎉 SUCCESS! Real hot dog flier created with Midjourney!")
        print(f"📂 Output directory: {self.output_dir}")
        print(f"🖼️ View flier: open {flier_path}")
        print("=" * 60)

if __name__ == "__main__":
    # Install dependencies if needed
    try:
        from dotenv import load_dotenv
        from PIL import Image
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.check_call(["pip", "install", "python-dotenv", "Pillow"])
        from dotenv import load_dotenv
        from PIL import Image
    
    # Run the workflow
    creator = RealHotDogFlier()
    asyncio.run(creator.run())

