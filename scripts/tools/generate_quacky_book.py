#!/usr/bin/env python3
"""
Simplified Children's Book Generator for Quacky McWaddles
Robust implementation with error handling and fallbacks
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Simple console output (no rich dependency issues)
def log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}.get(level, "•")
    print(f"[{timestamp}] {prefix} {message}")

class QuackyBookGenerator:
    """Generate Quacky McWaddles illustrated book with Midjourney."""
    
    def __init__(self):
        self.book_title = "Quacky McWaddles' Big Adventure"
        self.workflow_id = f"quacky_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = Path(f"quacky_book_output/{self.workflow_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Simple storage for generated content
        self.generated_images = {}
        self.book_pages = self._get_book_pages()
        
    def _get_book_pages(self) -> List[Dict[str, str]]:
        """Get key pages for the book with simplified prompts."""
        return [
            {
                "page": 1,
                "title": "Meet Quacky",
                "text": "Down by the sparkly pond lived a little yellow duckling named Quacky McWaddles. He had the BIGGEST orange feet you ever did see!",
                "prompt": "cute yellow duckling with huge orange webbed feet by a blue pond, children's book watercolor illustration, bright colors --ar 16:9 --v 6"
            },
            {
                "page": 3,
                "title": "Too Big Feet",
                "text": "Quacky looked at his enormous feet and sighed. The other ducklings giggled when he tripped over them.",
                "prompt": "sad yellow duckling looking at his oversized orange feet, other small ducklings nearby, watercolor style --ar 16:9 --v 6"
            },
            {
                "page": 5,
                "title": "Meeting Freddy Frog",
                "text": "In the meadow, Quacky met Freddy Frog. 'Are you wearing FLIPPERS?' croaked Freddy in amazement.",
                "prompt": "yellow duckling meeting green frog in flowery meadow, frog looking surprised at big orange feet, watercolor --ar 16:9 --v 6"
            },
            {
                "page": 7,
                "title": "The Waddle Hop",
                "text": "When his feet got tangled, Quacky invented a new dance - the WADDLE HOP! *BOING BOING BOING!*",
                "prompt": "yellow duckling hopping and dancing, motion lines, joyful expression, bunnies watching, watercolor --ar 16:9 --v 6"
            },
            {
                "page": 9,
                "title": "The Wise Goose",
                "text": "The Wise Old Goose smiled. 'Your big feet will make you the FASTEST swimmer! Your differences are your superpowers!'",
                "prompt": "wise white goose with tiny spectacles talking to excited yellow duckling on hilltop, sunset, watercolor --ar 16:9 --v 6"
            },
            {
                "page": 12,
                "title": "Happy Ending",
                "text": "Quacky won the swimming race! Now all the ducks wanted to learn the Waddle Hop. Being different was QUACK-A-DOODLE-AWESOME!",
                "prompt": "yellow duckling teaching other ducks to dance, celebration by pond, confetti water splashes, watercolor party scene --ar 16:9 --v 6"
            }
        ]
    
    async def test_midjourney_connection(self) -> bool:
        """Test if we can connect to Midjourney API."""
        try:
            from midjourney_integration.client import MidjourneyClient
            
            client = MidjourneyClient()
            log("Midjourney client initialized successfully", "SUCCESS")
            
            # Try a simple test request
            test_response = await client.submit_imagine(
                prompt="test connection yellow duck --ar 16:9",
                aspect_ratio="16:9",
                model_version="V_6",
                process_mode="relax"
            )
            
            if test_response:
                log(f"API connection successful! Response: {test_response.get('status', 'OK')}", "SUCCESS")
                return True
                
        except Exception as e:
            log(f"API connection test failed: {str(e)}", "ERROR")
            return False
    
    async def generate_illustration(self, page_data: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Generate a single illustration with error handling."""
        page_num = page_data["page"]
        
        try:
            from midjourney_integration.client import MidjourneyClient, poll_until_complete
            
            client = MidjourneyClient()
            log(f"Page {page_num}: Generating '{page_data['title']}'...")
            
            # Submit the imagine task
            response = await client.submit_imagine(
                prompt=page_data['prompt'],
                aspect_ratio="16:9",
                model_version="V_6",
                process_mode="relax"
            )
            
            # Extract task_id from various response formats
            task_id = None
            if isinstance(response, dict):
                if "data" in response:
                    task_id = response["data"].get("task_id")
                else:
                    task_id = response.get("task_id")
            
            if not task_id:
                log(f"Page {page_num}: No task_id received", "WARNING")
                return None
            
            log(f"Page {page_num}: Task ID: {task_id}")
            
            # Poll for completion
            result = await poll_until_complete(client, task_id, max_wait=120)
            
            # Extract image URL
            image_url = None
            if isinstance(result, dict):
                if "data" in result:
                    output = result["data"].get("output", {})
                else:
                    output = result.get("output", {})
                
                image_url = (output.get("image_url") or 
                           output.get("url") or
                           output.get("discord_image_url"))
            
            if image_url:
                log(f"Page {page_num}: Generated successfully!", "SUCCESS")
                return {
                    "page": page_num,
                    "title": page_data["title"],
                    "image_url": image_url,
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                log(f"Page {page_num}: No image URL in response", "WARNING")
                return None
                
        except Exception as e:
            log(f"Page {page_num}: Generation failed - {str(e)}", "ERROR")
            return None
    
    def create_book_markdown(self):
        """Create the final book markdown file."""
        md_path = self.output_dir / "quacky_book.md"
        
        content = f"# {self.book_title}\n\n"
        content += "*A Children's Book Adventure with Midjourney Illustrations*\n\n"
        content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
        
        # Add all 12 pages with text
        all_pages = {
            1: {"title": "Meet Quacky", "text": "Down by the sparkly pond lived a little yellow duckling named Quacky McWaddles. He had the BIGGEST orange feet!"},
            2: {"title": "Super Splash", "text": "Watch me do my SUPER SPLASH! *KER-SPLASH!* Oopsie, that was more of a belly-flop!"},
            3: {"title": "Too Big Feet", "text": "Holy mackerel! My feet are ENORMOUS! The other ducklings giggled when he tripped."},
            4: {"title": "Find the Wise Goose", "text": "I'll find the Wise Old Goose! She'll know what to do about my silly big feet!"},
            5: {"title": "Meeting Freddy", "text": "Are you wearing FLIPPERS? croaked Freddy Frog. Nope, these are my regular feet!"},
            6: {"title": "Tangled Up", "text": "Oh no! Quacky's big feet got tangled in the reedy grass. *TUG-TUG-TUG!*"},
            7: {"title": "The Waddle Hop", "text": "If he couldn't walk, he'd HOP! *BOING BOING!* I'm doing the WADDLE HOP!"},
            8: {"title": "More Friends", "text": "The bunnies loved Quacky's new dance. They all started doing the Waddle Hop together!"},
            9: {"title": "The Wise Goose", "text": "Your big feet will make you the FASTEST swimmer! Your differences are your SUPERPOWERS!"},
            10: {"title": "Racing Back", "text": "Quacky WADDLE-HOPPED all the way back to the pond. Who wants to RACE?"},
            11: {"title": "The Big Race", "text": "Into the pond they dove! Quacky's big feet went *ZOOM-ZOOM-ZOOM!* He was SO FAST!"},
            12: {"title": "Happy Ending", "text": "Quacky won! Being different was QUACK-A-DOODLE-AWESOME! Everyone did the Waddle Hop!"}
        }
        
        for page_num, page_content in all_pages.items():
            content += f"## Page {page_num}: {page_content['title']}\n\n"
            
            # Add image if we generated it
            if page_num in self.generated_images:
                img = self.generated_images[page_num]
                content += f"![{img['title']}]({img['image_url']})\n\n"
            
            content += f"{page_content['text']}\n\n"
            
            # Add interactive element
            if page_num == 1:
                content += "*🦆 Can YOU make a big splash sound?*\n\n"
            elif page_num == 7:
                content += "*🦆 Try doing the Waddle Hop! BOING BOING!*\n\n"
            elif page_num == 12:
                content += "*🦆 What makes YOU special and different?*\n\n"
            
            content += "---\n\n"
        
        # Add fun facts
        content += "## Fun Duck Facts! 🦆\n\n"
        content += "- Ducks have waterproof feathers!\n"
        content += "- Baby ducks can swim right after hatching!\n"
        content += "- Ducks sleep with one eye open!\n"
        content += "- A duck's quack DOES echo (despite the myth)!\n\n"
        content += "---\n\n"
        content += "*Remember: Being different makes you QUACK-A-DOODLE-AWESOME!*\n"
        
        md_path.write_text(content)
        log(f"Book created: {md_path}", "SUCCESS")
        return md_path
    
    def save_metadata(self):
        """Save generation metadata."""
        meta_path = self.output_dir / "metadata.json"
        
        metadata = {
            "title": self.book_title,
            "workflow_id": self.workflow_id,
            "generated_at": datetime.now().isoformat(),
            "pages_with_images": len(self.generated_images),
            "total_pages": 12,
            "illustrations": list(self.generated_images.values())
        }
        
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        log(f"Metadata saved: {meta_path}", "SUCCESS")
        return meta_path
    
    async def generate_book(self, test_only: bool = False):
        """Generate the complete illustrated book."""
        
        log("=" * 60)
        log(f"📚 GENERATING: {self.book_title}")
        log(f"Workflow ID: {self.workflow_id}")
        log("=" * 60)
        
        # Test connection first
        if not await self.test_midjourney_connection():
            log("Cannot connect to Midjourney API. Generating text-only version.", "WARNING")
            test_only = True
        
        if not test_only:
            # Generate illustrations for key pages
            log("\n🎨 Generating Midjourney Illustrations...")
            
            for page_data in self.book_pages:
                result = await self.generate_illustration(page_data)
                if result:
                    self.generated_images[result["page"]] = result
                    
                # Rate limiting
                await asyncio.sleep(2)
            
            log(f"\nGenerated {len(self.generated_images)}/{len(self.book_pages)} illustrations", "INFO")
        else:
            log("\n📝 Creating text-only version (test mode)", "INFO")
        
        # Create the book
        log("\n📖 Creating Book Files...")
        book_path = self.create_book_markdown()
        meta_path = self.save_metadata()
        
        # Final summary
        log("\n" + "=" * 60)
        log("✨ BOOK GENERATION COMPLETE! ✨", "SUCCESS")
        log(f"📁 Output Directory: {self.output_dir}")
        log(f"📖 Book File: {book_path.name}")
        log(f"📊 Metadata: {meta_path.name}")
        
        if self.generated_images:
            log(f"🎨 Illustrations: {len(self.generated_images)} pages with images")
        else:
            log("📝 Text-only version (no illustrations)")
        
        log("=" * 60)
        
        return {
            "success": True,
            "workflow_id": self.workflow_id,
            "book_path": str(book_path),
            "metadata_path": str(meta_path),
            "illustrations_count": len(self.generated_images)
        }


async def create_childrens_book(prompt: str = "create children's book") -> Dict[str, Any]:
    """
    Main entry point for creating a children's book.
    This function can be called with a simple prompt.
    """
    log(f"\n🚀 Received command: '{prompt}'")
    
    # Always generate the book - we're here to make it work!
    generator = QuackyBookGenerator()
    
    # Check if we should do test mode
    test_mode = "--test" in prompt or "test" in prompt.lower()
    
    result = await generator.generate_book(test_only=test_mode)
    return result


async def main():
    """Main entry point for command line execution."""
    import sys
    
    # Get command from arguments or use default
    command = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "create children's book"
    
    result = await create_childrens_book(command)
    
    if result["success"]:
        log("\n✅ Book generation successful!")
        log(f"View your book at: {result['book_path']}")
    else:
        log(f"\n❌ Generation failed: {result.get('error', 'Unknown error')}", "ERROR")


if __name__ == "__main__":
    # Check for API token
    if not os.getenv("MIDJOURNEY_API_TOKEN"):
        log("ERROR: MIDJOURNEY_API_TOKEN not found in environment", "ERROR")
        log("Please add MIDJOURNEY_API_TOKEN to your .env file", "INFO")
        exit(1)
    
    # Run the book generator
    asyncio.run(main())
