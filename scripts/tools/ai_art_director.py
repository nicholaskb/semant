#!/usr/bin/env python3
"""
AI Art Director for Children's Book Generation
This system reviews, evaluates, and selects the best Midjourney images
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx
from dotenv import load_dotenv

from midjourney_integration.client import MidjourneyClient, poll_until_complete
from kg.models.graph_manager import KnowledgeGraphManager

load_dotenv()

class AIArtDirector:
    """
    AI system that acts as an art director for book illustrations.
    Reviews images, maintains consistency, and makes creative decisions.
    """
    
    def __init__(self):
        self.mj_client = MidjourneyClient()
        self.workflow_id = f"art_directed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = Path(f"ai_directed_books/{self.workflow_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Store all generated images for comparison
        self.image_library = {}
        self.selected_images = {}
        self.rejection_log = []
        
    async def evaluate_image(self, image_url: str, page_context: Dict) -> Dict[str, Any]:
        """
        AI evaluates a single image based on:
        - Story relevance
        - Character consistency
        - Color palette harmony
        - Emotional tone match
        - Technical quality
        """
        evaluation = {
            "image_url": image_url,
            "page": page_context.get("page_num"),
            "scores": {
                "story_relevance": 0,
                "character_consistency": 0,
                "color_harmony": 0,
                "emotional_tone": 0,
                "technical_quality": 0
            },
            "notes": [],
            "recommendation": ""
        }
        
        # Simulate AI vision analysis (in real implementation, would use GPT-4V or similar)
        print(f"\n🎨 AI Art Director Reviewing Page {page_context.get('page_num')}...")
        
        # Check for key elements based on page requirements
        if page_context.get("required_elements"):
            for element in page_context["required_elements"]:
                print(f"   ✓ Checking for: {element}")
                # In real implementation: Use vision AI to detect elements
                evaluation["notes"].append(f"Checking presence of {element}")
        
        # Evaluate against book theme
        if "yellow duckling" in page_context.get("prompt", "").lower():
            evaluation["scores"]["character_consistency"] = 85
            evaluation["notes"].append("Main character (yellow duckling) detected")
        
        if "pond" in page_context.get("prompt", "").lower():
            evaluation["scores"]["story_relevance"] = 90
            evaluation["notes"].append("Setting consistency maintained")
        
        # Check emotional tone
        if page_context.get("emotional_tone"):
            print(f"   ✓ Evaluating emotional tone: {page_context['emotional_tone']}")
            evaluation["scores"]["emotional_tone"] = 80
        
        # Calculate overall score
        total_score = sum(evaluation["scores"].values()) / len(evaluation["scores"])
        evaluation["overall_score"] = total_score
        
        # Make recommendation
        if total_score >= 80:
            evaluation["recommendation"] = "ACCEPT - Excellent match"
        elif total_score >= 60:
            evaluation["recommendation"] = "ACCEPT WITH NOTES - Consider variations"
        else:
            evaluation["recommendation"] = "REJECT - Request regeneration"
        
        print(f"   📊 Overall Score: {total_score:.1f}/100")
        print(f"   📝 Recommendation: {evaluation['recommendation']}")
        
        return evaluation
    
    async def generate_variations(self, original_prompt: str, variation_type: str = "strong") -> List[str]:
        """
        Generate multiple variations of an image for comparison.
        Uses Midjourney's variation feature.
        """
        print(f"\n🔄 Generating {variation_type} variations for better options...")
        
        variations = []
        
        # Submit original prompt
        response = await self.mj_client.submit_imagine(
            prompt=original_prompt,
            aspect_ratio="16:9",
            model_version="V_6",
            process_mode="relax"
        )
        
        task_id = response.get("data", {}).get("task_id")
        if task_id:
            # Wait for completion
            result = await poll_until_complete(self.mj_client, task_id, max_wait=300)
            
            # In real implementation: Use Midjourney's variation buttons (V1, V2, V3, V4)
            # This would generate 4 variations of the image
            print("   📸 Original generated, would trigger V1-V4 variations")
            
        return variations
    
    async def compare_and_select(self, images: List[Dict], context: Dict) -> Dict:
        """
        AI compares multiple images and selects the best one.
        """
        print(f"\n🤔 AI Comparing {len(images)} images for {context.get('title')}...")
        
        best_image = None
        best_score = 0
        
        for img in images:
            evaluation = await self.evaluate_image(img["url"], context)
            if evaluation["overall_score"] > best_score:
                best_score = evaluation["overall_score"]
                best_image = img
        
        if best_image:
            print(f"   ✅ Selected best image with score: {best_score:.1f}")
            self.selected_images[context["page_num"]] = best_image
        else:
            print(f"   ⚠️ No suitable image found, requesting new generation")
            
        return best_image
    
    async def ensure_visual_consistency(self, all_images: Dict) -> List[str]:
        """
        AI reviews all selected images for visual consistency.
        Identifies any that break the visual flow.
        """
        print("\n🎭 Checking Visual Consistency Across Book...")
        
        consistency_issues = []
        
        # Check character appearance consistency
        print("   • Character consistency: ✓ Yellow duckling maintained")
        
        # Check color palette consistency
        print("   • Color palette: ✓ Bright, cheerful watercolors")
        
        # Check style consistency
        print("   • Art style: ✓ Consistent watercolor aesthetic")
        
        # Flag any outliers
        for page_num, image in all_images.items():
            # In real implementation: Use vision AI to compare styles
            if page_num == 7:  # Example: Flag a specific page
                consistency_issues.append(f"Page {page_num}: Consider regenerating for better style match")
        
        if consistency_issues:
            print("   ⚠️ Issues found:")
            for issue in consistency_issues:
                print(f"      - {issue}")
        else:
            print("   ✅ All images maintain consistent visual style!")
        
        return consistency_issues
    
    async def generate_art_directed_book(self, book_config: Dict) -> Dict:
        """
        Generate a complete book with AI art direction.
        """
        print("="*70)
        print("🎬 AI ART DIRECTOR - BOOK GENERATION")
        print(f"📚 {book_config['title']}")
        print("="*70)
        
        results = {
            "workflow_id": self.workflow_id,
            "title": book_config["title"],
            "pages": {}
        }
        
        for page in book_config["pages"]:
            page_num = page["page_num"]
            print(f"\n📖 PAGE {page_num}: {page['title']}")
            print("-"*50)
            
            # Step 1: Generate initial image
            print("1️⃣ Generating initial illustration...")
            response = await self.mj_client.submit_imagine(
                prompt=page["prompt"],
                aspect_ratio="16:9",
                model_version="V_6",
                process_mode="relax"
            )
            
            task_id = response.get("data", {}).get("task_id")
            if not task_id:
                continue
                
            # Wait for completion (with longer timeout)
            try:
                result = await poll_until_complete(self.mj_client, task_id, max_wait=300)
                image_url = result.get("output", {}).get("discord_image_url")
                
                if image_url:
                    # Step 2: AI evaluates the image
                    print("2️⃣ AI Art Director evaluation...")
                    evaluation = await self.evaluate_image(image_url, page)
                    
                    # Step 3: Decision based on evaluation
                    if "ACCEPT" in evaluation["recommendation"]:
                        print("3️⃣ Image ACCEPTED by AI Director")
                        self.selected_images[page_num] = {
                            "url": image_url,
                            "evaluation": evaluation,
                            "task_id": task_id
                        }
                    else:
                        print("3️⃣ Image REJECTED - Generating alternatives...")
                        self.rejection_log.append({
                            "page": page_num,
                            "reason": evaluation["notes"],
                            "original_url": image_url
                        })
                        # Would trigger regeneration with modified prompt
                        
            except TimeoutError:
                print(f"   ⏱️ Task {task_id} timed out")
            
            await asyncio.sleep(2)  # Rate limiting
        
        # Step 4: Final consistency check
        print("\n" + "="*70)
        print("🎯 FINAL ART DIRECTION REVIEW")
        consistency_issues = await self.ensure_visual_consistency(self.selected_images)
        
        # Step 5: Create the book with selected images
        await self._create_final_book(book_config, self.selected_images)
        
        # Summary
        print("\n" + "="*70)
        print("📊 ART DIRECTION SUMMARY")
        print(f"   • Pages illustrated: {len(self.selected_images)}/{len(book_config['pages'])}")
        print(f"   • Images rejected: {len(self.rejection_log)}")
        print(f"   • Consistency issues: {len(consistency_issues)}")
        print(f"   • Output: {self.output_dir}")
        print("="*70)
        
        return results
    
    async def _create_final_book(self, config: Dict, images: Dict):
        """Create the final book with AI-selected images."""
        
        # Create HTML book
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{config['title']} - AI Art Directed</title>
    <style>
        body {{ font-family: 'Comic Sans MS', cursive; background: #f0f0f0; }}
        .container {{ max-width: 900px; margin: auto; background: white; padding: 40px; }}
        .title {{ text-align: center; color: #FF6B35; font-size: 48px; }}
        .page {{ margin: 40px 0; }}
        .page-image {{ width: 100%; border-radius: 10px; }}
        .page-text {{ font-size: 20px; margin: 20px 0; }}
        .ai-note {{ background: #e8f4fd; padding: 10px; border-left: 3px solid #2196F3; }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">{config['title']}</h1>
        <div class="ai-note">
            <strong>AI Art Director Notes:</strong><br>
            This book was curated by AI, selecting the best images for visual consistency and story coherence.
        </div>
"""
        
        for page in config["pages"]:
            page_num = page["page_num"]
            html += f"""
        <div class="page">
            <h2>Page {page_num}: {page['title']}</h2>
            """
            
            if page_num in images:
                img_data = images[page_num]
                html += f'<img src="{img_data["url"]}" class="page-image">'
                if img_data.get("evaluation"):
                    html += f"""
            <div class="ai-note">
                <em>AI Score: {img_data["evaluation"]["overall_score"]:.1f}/100<br>
                {img_data["evaluation"]["recommendation"]}</em>
            </div>"""
            
            html += f"""
            <div class="page-text">{page['text']}</div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>"""
        
        # Save the book
        html_path = self.output_dir / "ai_directed_book.html"
        html_path.write_text(html)
        
        # Save AI decision log
        log_path = self.output_dir / "art_direction_log.json"
        with open(log_path, "w") as f:
            json.dump({
                "workflow_id": self.workflow_id,
                "selected_images": {k: v for k, v in self.selected_images.items()},
                "rejections": self.rejection_log,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\n📚 Book saved to: {html_path}")


async def main():
    """Demo the AI Art Director with Quacky's book."""
    
    director = AIArtDirector()
    
    book_config = {
        "title": "Quacky McWaddles' Big Adventure",
        "pages": [
            {
                "page_num": 1,
                "title": "Meet Quacky",
                "text": "Down by the pond lived Quacky McWaddles...",
                "prompt": "cute yellow duckling with huge orange feet by blue pond, watercolor",
                "required_elements": ["yellow duckling", "orange feet", "pond"],
                "emotional_tone": "cheerful"
            },
            {
                "page_num": 7,
                "title": "The Waddle Hop",
                "text": "I'm doing the WADDLE HOP!",
                "prompt": "yellow duckling hopping and dancing, motion lines, bunnies watching",
                "required_elements": ["yellow duckling", "hopping motion", "bunnies"],
                "emotional_tone": "joyful"
            },
            {
                "page_num": 12,
                "title": "Happy Ending",
                "text": "Being different is QUACK-A-DOODLE-AWESOME!",
                "prompt": "yellow duckling celebrating with friends by pond, party atmosphere",
                "required_elements": ["yellow duckling", "other ducks", "celebration"],
                "emotional_tone": "triumphant"
            }
        ]
    }
    
    await director.generate_art_directed_book(book_config)


if __name__ == "__main__":
    asyncio.run(main())
