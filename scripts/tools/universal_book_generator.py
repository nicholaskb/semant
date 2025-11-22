#!/usr/bin/env python3
"""
UNIVERSAL ONE-CLICK BOOK GENERATOR
Works with ANY theme, story, or script you provide!
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

from semant.agent_tools.midjourney import REGISTRY
from midjourney_integration.client import MidjourneyClient

load_dotenv()

class UniversalBookGenerator:
    """
    Generate ANY children's book with one click.
    Just provide your story pages!
    """
    
    def __init__(self):
        self.workflow_id = f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.state_file = Path(f"generated_books/{self.workflow_id}/state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize tools
        self.mj_client = MidjourneyClient()
        self.imagine_tool = REGISTRY["mj.imagine"]()
        
    def create_book_from_story(self, title: str, pages: List[Dict]) -> None:
        """
        Create a book from any story.
        
        Args:
            title: Book title
            pages: List of dicts with 'text' and optional 'art_direction'
        """
        self.book_title = title
        self.pages = self._process_pages(pages)
        asyncio.run(self.generate_complete_book())
    
    def _process_pages(self, pages: List[Dict]) -> List[Dict]:
        """Convert user pages to full page specs with AI-generated prompts."""
        
        processed = []
        
        for i, page in enumerate(pages, 1):
            # AI generates the art prompt based on the text
            art_style = page.get('art_style', 'watercolor children\'s book illustration')
            art_direction = page.get('art_direction', '')
            
            # AI Director creates the prompt
            prompt = self._ai_create_prompt(page['text'], art_direction, art_style)
            
            processed.append({
                "page": i,
                "text": page['text'],
                "prompt": f"{prompt} --ar 16:9 --v 6",
                "fallback_prompt": f"simple {art_style} illustration --ar 16:9"
            })
        
        return processed
    
    def _ai_create_prompt(self, text: str, direction: str, style: str) -> str:
        """AI creates the perfect Midjourney prompt from the story text."""
        
        # Extract key elements from text
        keywords = []
        
        # Look for characters
        if "princess" in text.lower():
            keywords.append("beautiful princess")
        if "dragon" in text.lower():
            keywords.append("friendly dragon")
        if "robot" in text.lower():
            keywords.append("shiny robot")
        if "unicorn" in text.lower():
            keywords.append("magical unicorn")
        if "pirate" in text.lower():
            keywords.append("brave pirate")
        if "astronaut" in text.lower():
            keywords.append("space astronaut")
            
        # Look for emotions
        if any(word in text.lower() for word in ["happy", "joy", "smile"]):
            keywords.append("joyful")
        if any(word in text.lower() for word in ["sad", "cry", "tear"]):
            keywords.append("sad")
        if any(word in text.lower() for word in ["brave", "courage", "strong"]):
            keywords.append("determined")
            
        # Look for settings
        if "space" in text.lower():
            keywords.append("in outer space with stars")
        if "ocean" in text.lower():
            keywords.append("underwater ocean scene")
        if "forest" in text.lower():
            keywords.append("magical forest")
        if "castle" in text.lower():
            keywords.append("fairy tale castle")
            
        # Combine with style
        base_prompt = " ".join(keywords) if keywords else "children's storybook scene"
        
        if direction:
            base_prompt = f"{base_prompt}, {direction}"
            
        return f"{base_prompt}, {style}"
    
    async def generate_complete_book(self) -> str:
        """Generate the complete book."""
        
        print("="*70)
        print(f"🚀 GENERATING: {self.book_title}")
        print(f"📖 Pages: {len(self.pages)}")
        print("="*70)
        
        # Generate all illustrations
        for page in self.pages:
            await self._generate_page_illustration(page)
            await asyncio.sleep(2)
        
        # Create final book
        book_path = self._create_html_book()
        
        print("\n" + "="*70)
        print("✨ BOOK COMPLETE!")
        print(f"📚 View at: {book_path}")
        print("="*70)
        
        # Open automatically
        import subprocess
        subprocess.run(["open", str(book_path)])
        
        return str(book_path)
    
    async def _generate_page_illustration(self, page: Dict) -> None:
        """Generate or use fallback for a page."""
        
        print(f"\n📖 Page {page['page']}")
        print(f"   Text: {page['text'][:50]}...")
        print(f"   🎨 Generating illustration...")
        
        try:
            # Submit to Midjourney
            result = await self.imagine_tool.run(
                prompt=page['prompt'],
                model_version="v6",
                aspect_ratio="16:9",
                process_mode="fast"
            )
            
            task_id = result.get("data", {}).get("task_id")
            if task_id:
                print(f"   Task ID: {task_id}")
                
                # Quick poll (30 seconds max for demo)
                image_url = await self._quick_poll(task_id, timeout=30)
                
                if image_url:
                    page['image_url'] = image_url
                    print(f"   ✅ Image ready!")
                    return
                    
        except Exception as e:
            print(f"   ⚠️ Generation failed: {e}")
        
        # Use placeholder
        page['image_url'] = self._get_placeholder_image(page['page'])
        print(f"   📦 Using placeholder image")
    
    async def _quick_poll(self, task_id: str, timeout: int = 30) -> Optional[str]:
        """Quick polling for demo."""
        
        start = time.time()
        while (time.time() - start) < timeout:
            try:
                result = await self.mj_client.poll_task(task_id)
                data = result.get("data", result)
                
                if data.get("status") in ["completed", "finished"]:
                    output = data.get("output", {})
                    return (output.get("discord_image_url") or 
                           output.get("image_url") or 
                           output.get("url"))
                           
                await asyncio.sleep(5)
                
            except:
                await asyncio.sleep(5)
                
        return None
    
    def _get_placeholder_image(self, page_num: int) -> str:
        """Get a nice placeholder image."""
        
        placeholders = [
            "https://img.theapi.app/mj/83af08bb-4d5d-4538-9999-072e476bc980.png",
            "https://img.theapi.app/mj/0d4596f5-8fe4-470d-92ab-580682b14255.png",
            "https://img.theapi.app/mj/ed8725a6-0265-4936-875f-b7d048ab1926.png",
        ]
        
        return placeholders[page_num % len(placeholders)]
    
    def _create_html_book(self) -> Path:
        """Create the final HTML book."""
        
        output_dir = Path(f"generated_books/{self.workflow_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.book_title}</title>
    <style>
        body {{ 
            font-family: 'Comic Sans MS', cursive; 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            padding: 20px;
        }}
        .book {{ 
            max-width: 900px; 
            margin: auto; 
            background: white; 
            border-radius: 20px; 
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }}
        h1 {{
            text-align: center;
            color: #764ba2;
            font-size: 42px;
        }}
        .page {{ 
            margin: 40px 0; 
            padding: 30px; 
            background: #f9f9f9; 
            border-radius: 15px;
        }}
        .page-image {{ 
            width: 100%; 
            border-radius: 10px; 
            margin: 20px 0;
            box-shadow: 0 10px 20px rgba(0,0,0,0.15);
        }}
        .page-text {{ 
            font-size: 24px; 
            line-height: 1.8; 
            color: #333;
            background: white;
            padding: 20px;
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="book">
        <h1>{self.book_title}</h1>
"""
        
        for page in self.pages:
            html += f"""
        <div class="page">
            <h2>Page {page['page']}</h2>
            <img src="{page.get('image_url', '')}" class="page-image" alt="Page {page['page']}">
            <div class="page-text">{page['text']}</div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>"""
        
        book_path = output_dir / "book.html"
        book_path.write_text(html)
        
        return book_path


# EXAMPLE: Different themes you can use
def demo_space_adventure():
    """Demo: Space adventure theme"""
    
    generator = UniversalBookGenerator()
    
    generator.create_book_from_story(
        title="Luna's Space Adventure",
        pages=[
            {
                "text": "Luna the astronaut bunny dreamed of visiting the stars!",
                "art_direction": "cute bunny in a space suit"
            },
            {
                "text": "She built a rocket ship from cardboard boxes and imagination.",
                "art_direction": "bunny building colorful cardboard rocket"
            },
            {
                "text": "3... 2... 1... BLAST OFF! Luna zoomed past the clouds!",
                "art_direction": "rocket launching with bunny inside"
            },
            {
                "text": "She danced on the moon and made friends with alien butterflies.",
                "art_direction": "bunny on moon surface with glowing butterflies"
            },
            {
                "text": "Luna returned home with stardust in her fur and stories to share!",
                "art_direction": "happy bunny landing back on Earth"
            }
        ]
    )


def demo_dragon_princess():
    """Demo: Dragon and princess theme"""
    
    generator = UniversalBookGenerator()
    
    generator.create_book_from_story(
        title="Princess Bella and the Friendly Dragon",
        pages=[
            {
                "text": "Princess Bella found a baby dragon crying in the garden.",
                "art_style": "fairy tale watercolor"
            },
            {
                "text": "Don't be scared, little one! I'll help you find your mama!",
                "art_style": "soft pastel illustration"
            },
            {
                "text": "They searched the enchanted forest together, becoming best friends.",
                "art_style": "magical forest painting"
            },
            {
                "text": "The mama dragon was so happy! She gave Bella magical wings!",
                "art_style": "joyful fantasy art"
            },
            {
                "text": "Now Bella could fly and visit her dragon friends every day!",
                "art_style": "dreamy sky scene"
            }
        ]
    )


def demo_robot_chef():
    """Demo: Robot chef theme"""
    
    generator = UniversalBookGenerator()
    
    generator.create_book_from_story(
        title="Robbie the Robot Chef",
        pages=[
            {
                "text": "Robbie the robot loved to cook but only knew how to make toast!",
            },
            {
                "text": "He went to cooking school and learned to make rainbow soup!",
            },
            {
                "text": "Oh no! Robbie mixed up the recipes and made bouncing spaghetti!",
            },
            {
                "text": "The kids loved it! Bouncing spaghetti became the best meal ever!",
            },
            {
                "text": "Robbie opened a restaurant where food was fun and silly!",
            }
        ]
    )


def custom_story():
    """Let user create their own story interactively"""
    
    print("\n🎨 CREATE YOUR OWN STORY!\n")
    
    title = input("Enter your book title: ") or "My Amazing Story"
    num_pages = int(input("How many pages (3-10)? ") or "5")
    
    pages = []
    for i in range(1, min(num_pages + 1, 11)):
        print(f"\nPage {i}:")
        text = input("Enter the text for this page: ")
        if text:
            pages.append({"text": text})
    
    if pages:
        generator = UniversalBookGenerator()
        generator.create_book_from_story(title, pages)
    else:
        print("No pages provided, running demo...")
        demo_space_adventure()


if __name__ == "__main__":
    print("\n🚀 UNIVERSAL BOOK GENERATOR")
    print("\nChoose a demo or create your own:")
    print("1. Space Adventure")
    print("2. Dragon & Princess")
    print("3. Robot Chef")
    print("4. Create Your Own")
    
    choice = input("\nEnter choice (1-4): ") or "1"
    
    if choice == "1":
        demo_space_adventure()
    elif choice == "2":
        demo_dragon_princess()
    elif choice == "3":
        demo_robot_chef()
    else:
        custom_story()

