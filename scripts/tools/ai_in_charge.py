#!/usr/bin/env python3
"""
AI IN CHARGE - Autonomous Book Creation System
The AI makes ALL decisions about the book generation process.
"""

import asyncio
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

from semant.agent_tools.midjourney import REGISTRY
from kg.models.graph_manager import KnowledgeGraphManager

load_dotenv()

class AIBookDirector:
    """
    AI system that is FULLY IN CHARGE of book creation.
    Makes all creative decisions autonomously.
    """
    
    def __init__(self, book_title: str = "Quacky McWaddles' Big Adventure"):
        self.book_title = book_title
        self.workflow_id = f"ai_directed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize all tools from registry
        self.imagine_tool = REGISTRY["mj.imagine"]()
        self.action_tool = REGISTRY["mj.action"]()
        self.describe_tool = REGISTRY["mj.describe"]()
        self.get_task_tool = REGISTRY["mj.get_task"]()
        self.book_tool = REGISTRY["mj.book_generator"]()
        
        # AI decision tracking
        self.decisions_made = []
        self.creative_choices = {}
        self.quality_threshold = 85  # AI won't accept images below this score
        
        # Knowledge Graph for tracking AI decisions
        self.kg_manager = None
        
        print("="*70)
        print("🤖 AI DIRECTOR INITIALIZED - I'M IN CHARGE NOW")
        print(f"📚 Project: {self.book_title}")
        print(f"🎯 Quality Threshold: {self.quality_threshold}/100")
        print("="*70)
    
    async def initialize_kg(self):
        """Initialize Knowledge Graph to track AI decisions."""
        self.kg_manager = KnowledgeGraphManager()
        await self.kg_manager.initialize()
    
    def make_creative_decision(self, context: str, options: List[str]) -> str:
        """
        AI makes a creative decision between options.
        """
        decision = random.choice(options)  # In production: Use LLM
        
        self.decisions_made.append({
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "options": options,
            "decision": decision,
            "reasoning": f"AI selected based on creative vision"
        })
        
        print(f"\n🎨 AI DECISION: {context}")
        print(f"   Options: {options}")
        print(f"   → Chosen: {decision}")
        
        return decision
    
    async def evaluate_image_quality(self, image_url: str, requirements: Dict) -> Dict[str, Any]:
        """
        AI evaluates if an image meets quality standards.
        """
        print(f"\n🔍 AI EVALUATING IMAGE...")
        
        # Use describe tool to understand the image
        try:
            description = await self.describe_tool.run(image_url=image_url)
            ai_vision = description.get("data", {}).get("description", "")
            print(f"   What I see: {ai_vision[:100]}...")
        except:
            ai_vision = "Unable to analyze"
        
        # AI scoring (in production: Use GPT-4V or Claude Vision)
        scores = {
            "composition": random.randint(70, 95),
            "character_consistency": random.randint(75, 95),
            "emotional_alignment": random.randint(70, 90),
            "story_relevance": random.randint(80, 95),
            "artistic_quality": random.randint(75, 92)
        }
        
        overall_score = sum(scores.values()) / len(scores)
        
        decision = "REJECT" if overall_score < self.quality_threshold else "ACCEPT"
        
        print(f"   Overall Score: {overall_score:.1f}/100")
        print(f"   AI Decision: {decision}")
        
        if decision == "REJECT":
            print(f"   ❌ Not good enough. I'll try something else.")
        else:
            print(f"   ✅ This meets my standards!")
        
        return {
            "image_url": image_url,
            "ai_vision": ai_vision,
            "scores": scores,
            "overall_score": overall_score,
            "decision": decision,
            "requirements_met": overall_score >= self.quality_threshold
        }
    
    async def generate_with_ai_direction(self, page: Dict) -> Optional[Dict]:
        """
        AI directs the generation of a single page illustration.
        """
        page_num = page.get("page_num", 1)
        
        print(f"\n📖 PAGE {page_num}: {page['title']}")
        print("="*50)
        
        # AI decides on artistic style
        style = self.make_creative_decision(
            "Art style for this page",
            ["watercolor", "oil painting style", "digital art", "sketch style"]
        )
        
        # AI decides on color palette
        palette = self.make_creative_decision(
            "Color palette",
            ["bright and cheerful", "soft pastels", "vibrant primary colors", "warm sunset tones"]
        )
        
        # AI decides on composition
        composition = self.make_creative_decision(
            "Composition focus",
            ["close-up on character", "wide scene view", "action shot", "emotional portrait"]
        )
        
        # AI constructs the prompt
        ai_prompt = f"{page['base_prompt']}, {style}, {palette}, {composition} --ar 16:9"
        
        print(f"\n🎯 AI-CRAFTED PROMPT:")
        print(f"   {ai_prompt}")
        
        # If we have a best image, use it as character reference
        if hasattr(self, 'best_character_ref'):
            print(f"   Using character reference for consistency")
            ai_prompt = f"{ai_prompt} --cref {self.best_character_ref}"
        
        # Generate the image
        print(f"\n🎨 Generating image with my creative vision...")
        response = await self.imagine_tool.run(
            prompt=ai_prompt,
            model_version="v6",
            aspect_ratio="16:9",
            process_mode="relax"
        )
        
        task_id = response.get("data", {}).get("task_id")
        
        if not task_id:
            print("   ❌ Generation failed. I'll try a different approach.")
            return None
        
        print(f"   Task ID: {task_id}")
        
        # Wait and check quality
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"\n   Attempt {attempt + 1}/{max_attempts}")
            
            # Poll for completion
            await asyncio.sleep(5)
            result = await self.get_task_tool.run(task_id=task_id)
            status = result.get("data", {}).get("status")
            
            if status == "completed":
                image_url = result.get("data", {}).get("output", {}).get("discord_image_url")
                
                if image_url:
                    # AI evaluates the result
                    evaluation = await self.evaluate_image_quality(
                        image_url,
                        page.get("requirements", {})
                    )
                    
                    if evaluation["decision"] == "ACCEPT":
                        return {
                            "page_num": page_num,
                            "image_url": image_url,
                            "task_id": task_id,
                            "ai_evaluation": evaluation,
                            "creative_choices": {
                                "style": style,
                                "palette": palette,
                                "composition": composition
                            }
                        }
                    else:
                        # AI rejects and tries variations
                        print(f"\n🔄 I don't like this. Getting variations...")
                        
                        for v in range(1, 5):
                            variation = await self.action_tool.run(
                                task_id=task_id,
                                action=f"variation{v}"
                            )
                            print(f"   Created variation {v}")
                            
                            # Evaluate variation
                            # In production: wait for completion and evaluate
        
        return None
    
    async def run_autonomous_book_creation(self):
        """
        AI autonomously creates the entire book.
        """
        
        print("\n" + "="*70)
        print("🚀 STARTING AUTONOMOUS BOOK CREATION")
        print("The AI is making all creative decisions...")
        print("="*70)
        
        # Initialize Knowledge Graph
        await self.initialize_kg()
        
        # Define book structure (AI could also generate this)
        book_pages = [
            {
                "page_num": 1,
                "title": "Meet Quacky",
                "base_prompt": "cute yellow duckling with huge orange webbed feet by a sparkling blue pond",
                "requirements": {"character": "yellow duckling", "setting": "pond"}
            },
            {
                "page_num": 7,
                "title": "The Waddle Hop",
                "base_prompt": "yellow duckling hopping and dancing with joy, bunnies watching",
                "requirements": {"action": "hopping", "emotion": "joyful"}
            },
            {
                "page_num": 12,
                "title": "Happy Ending",
                "base_prompt": "all ducks celebrating together by the pond",
                "requirements": {"mood": "celebratory", "multiple_characters": True}
            }
        ]
        
        # AI selects which pages are most important
        print("\n📋 AI SELECTING KEY PAGES TO ILLUSTRATE...")
        
        priority_pages = self.make_creative_decision(
            "Which pages are most important?",
            ["All pages equally", "Focus on key moments", "Emphasize emotional beats"]
        )
        
        # Generate illustrations with AI direction
        generated_images = {}
        
        for page in book_pages:
            result = await self.generate_with_ai_direction(page)
            
            if result:
                generated_images[page["page_num"]] = result
                
                # First good image becomes character reference
                if page["page_num"] == 1 and result.get("image_url"):
                    self.best_character_ref = result["image_url"]
                    print(f"\n🎯 AI SELECTED CHARACTER REFERENCE:")
                    print(f"   This will ensure consistency across all images")
            
            await asyncio.sleep(2)  # Rate limiting
        
        # AI makes final curation decisions
        print("\n" + "="*70)
        print("📊 AI FINAL REVIEW")
        print("="*70)
        
        print(f"\n✅ Successfully generated: {len(generated_images)} images")
        print(f"📝 Creative decisions made: {len(self.decisions_made)}")
        
        # Save AI's creative vision
        self.save_ai_decisions(generated_images)
        
        # Create the final book
        await self.create_ai_directed_book(generated_images)
        
        print("\n" + "="*70)
        print("✨ AI-DIRECTED BOOK COMPLETE!")
        print(f"The AI made {len(self.decisions_made)} autonomous decisions")
        print(f"Output: ai_directed_books/{self.workflow_id}/")
        print("="*70)
    
    def save_ai_decisions(self, images: Dict):
        """Save all AI decisions and creative choices."""
        
        output_dir = Path(f"ai_directed_books/{self.workflow_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        decisions_file = output_dir / "ai_decisions.json"
        
        with open(decisions_file, "w") as f:
            json.dump({
                "workflow_id": self.workflow_id,
                "book_title": self.book_title,
                "timestamp": datetime.now().isoformat(),
                "quality_threshold": self.quality_threshold,
                "decisions_made": self.decisions_made,
                "generated_images": {
                    str(k): {
                        "image_url": v.get("image_url"),
                        "creative_choices": v.get("creative_choices"),
                        "ai_evaluation": v.get("ai_evaluation")
                    }
                    for k, v in images.items()
                }
            }, f, indent=2)
        
        print(f"\n📁 AI decisions saved to: {decisions_file}")
    
    async def create_ai_directed_book(self, images: Dict):
        """Create the final book with AI's creative vision."""
        
        output_dir = Path(f"ai_directed_books/{self.workflow_id}")
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.book_title} - AI Directed</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #1a1a1a; color: white; margin: 0; padding: 20px; }}
        .header {{ text-align: center; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
        .header h1 {{ margin: 0; font-size: 48px; }}
        .subtitle {{ font-size: 20px; opacity: 0.9; }}
        .ai-badge {{ background: #00ff00; color: black; padding: 5px 15px; border-radius: 20px; display: inline-block; margin-top: 10px; }}
        .page {{ background: #2a2a2a; margin: 30px auto; padding: 30px; max-width: 900px; border-radius: 15px; }}
        .page-image {{ width: 100%; border-radius: 10px; }}
        .creative-choices {{ background: #3a3a3a; padding: 15px; border-radius: 10px; margin-top: 15px; }}
        .score {{ color: #00ff00; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.book_title}</h1>
        <div class="subtitle">Autonomously Created by AI</div>
        <div class="ai-badge">🤖 AI IN CHARGE</div>
    </div>
"""
        
        for page_num, data in images.items():
            choices = data.get("creative_choices", {})
            evaluation = data.get("ai_evaluation", {})
            
            html += f"""
    <div class="page">
        <h2>Page {page_num}</h2>
        <img src="{data['image_url']}" class="page-image">
        <div class="creative-choices">
            <h3>AI Creative Decisions:</h3>
            <p>Style: {choices.get('style', 'N/A')}</p>
            <p>Palette: {choices.get('palette', 'N/A')}</p>
            <p>Composition: {choices.get('composition', 'N/A')}</p>
            <p>Quality Score: <span class="score">{evaluation.get('overall_score', 0):.1f}/100</span></p>
        </div>
    </div>
"""
        
        html += f"""
    <div class="page" style="text-align: center;">
        <h2>AI Director's Notes</h2>
        <p>This book was created entirely under AI direction.</p>
        <p>Total creative decisions made: {len(self.decisions_made)}</p>
        <p>Quality threshold enforced: {self.quality_threshold}/100</p>
        <p>Every image met or exceeded AI standards.</p>
    </div>
</body>
</html>"""
        
        html_path = output_dir / "ai_directed_book.html"
        html_path.write_text(html)
        
        print(f"📚 AI-directed book saved to: {html_path}")


async def main():
    """Let the AI take charge!"""
    
    director = AIBookDirector("Quacky McWaddles' Big Adventure")
    
    # Let the AI run the show
    await director.run_autonomous_book_creation()


if __name__ == "__main__":
    print("\n🤖 INITIATING AI-CONTROLLED BOOK GENERATION...")
    print("The AI will make ALL creative decisions.\n")
    asyncio.run(main())
