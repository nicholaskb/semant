#!/usr/bin/env python3
"""
Image generation integration for Brain Rot project.

Uses Midjourney integration to generate viral images.
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.cloud import storage
from loguru import logger

from scripts.brainrot.config import config

# Import Midjourney client
try:
    from midjourney_integration.client import MidjourneyClient
    MIDJOURNEY_AVAILABLE = True
except ImportError:
    MIDJOURNEY_AVAILABLE = False
    logger.warning("Midjourney client not available")


class ImageGenerator:
    """Generate images from combinations."""
    
    def __init__(self):
        """Initialize image generator."""
        self.midjourney_client = None
        if MIDJOURNEY_AVAILABLE:
            try:
                self.midjourney_client = MidjourneyClient()
                logger.info("✅ Midjourney client initialized")
            except Exception as e:
                logger.warning(f"Midjourney client initialization failed: {e}")
    
    async def generate_images_for_combinations(
        self,
        combinations: List[Dict[str, Any]],
        variations_per_combo: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Generate images for combinations.
        
        Args:
            combinations: List of combination dictionaries
            variations_per_combo: Number of image variations per combination
            
        Returns:
            List of generated images with metadata
        """
        if not self.midjourney_client:
            logger.error("Midjourney client not available")
            return []
        
        generated_images = []
        
        if not combinations:
            logger.warning("No combinations provided for image generation")
            return []
        
        for combo in combinations:
            if not isinstance(combo, dict):
                logger.warning(f"Skipping invalid combination: {combo}")
                continue
            
            combo_prompt = combo.get("combined_prompt", "")
            if not combo_prompt:
                # Create prompt from combination
                combo_prompt = self._create_image_prompt(combo)
                if not combo_prompt:
                    logger.warning(f"Could not create prompt for combination: {combo}")
                    continue
            
            logger.info(f"Generating images for: {combo_prompt}")
            
            for variation in range(variations_per_combo):
                try:
                    # Enhance prompt with style
                    enhanced_prompt = self._enhance_prompt(combo_prompt, variation)
                    
                    # Submit to Midjourney
                    # Note: aspect_ratio should be None or valid format like "16:9", "9:16", "1:1"
                    result = await self.midjourney_client.submit_imagine(
                        prompt=enhanced_prompt,
                        aspect_ratio=config.aspect_ratio if config.aspect_ratio else None,
                        process_mode="fast",  # Use fast mode for speed
                        model_version="v7"  # Use latest model
                    )
                    
                    if result and "task_id" in result:
                        # Generate unique combination ID if not present
                        combo_id = combo.get("id") or combo.get("combination_id") or hash(str(combo.get("combined_prompt", "")))
                        image_data = {
                            "combination_id": combo_id,
                            "prompt": enhanced_prompt,
                            "original_combo": combo,
                            "task_id": result["task_id"],
                            "variation": variation + 1,
                            "status": "pending"
                        }
                        generated_images.append(image_data)
                        logger.info(f"  ✅ Submitted variation {variation + 1}")
                    else:
                        logger.warning(f"  ⚠️  Failed to submit variation {variation + 1}")
                    
                    # Rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Failed to generate image for variation {variation + 1}: {e}")
                    continue
        
        return generated_images
    
    def _create_image_prompt(self, combo: Dict[str, Any]) -> str:
        """Create image prompt from combination."""
        american_objs = combo.get("american_objects", [])
        italian_phrases = combo.get("italian_phrases", [])
        
        # Ensure we have valid lists
        if not american_objs or not italian_phrases:
            return ""
        
        american = ", ".join(str(x) for x in american_objs)
        italian = ", ".join(str(x) for x in italian_phrases)
        return f"{italian} with {american}"
    
    def _enhance_prompt(self, base_prompt: str, variation: int) -> str:
        """Enhance prompt with style and variation."""
        style_additions = [
            f", {config.image_style}",
            ", high quality, viral meme style",
            ", trending on social media",
            ", absurdist humor",
            ", colorful and eye-catching"
        ]
        
        # Add variation-specific elements
        variation_styles = [
            ", close-up shot",
            ", wide angle view",
            ", dramatic lighting",
            ", minimalist style"
        ]
        
        enhanced = base_prompt
        # Add style (always include base style)
        enhanced += style_additions[0] if style_additions else ""
        # Add variation-specific style
        if variation_styles:
            enhanced += variation_styles[variation % len(variation_styles)]
        
        return enhanced
    
    def save_to_gcs(
        self,
        image_data: List[Dict[str, Any]]
    ) -> str:
        """Save image generation data to GCS."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(config.gcs_bucket_name)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_images/generation_log_{timestamp}.json"
        
        blob = bucket.blob(filename)
        blob.upload_from_string(
            json.dumps(image_data, indent=2),
            content_type="application/json"
        )
        
        logger.info(f"Saved {len(image_data)} image generation records to gs://{config.gcs_bucket_name}/{filename}")
        return filename


async def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Image Generation")
    logger.info("=" * 60)
    
    if not MIDJOURNEY_AVAILABLE:
        logger.error("Midjourney client not available. Check MIDJOURNEY_API_TOKEN.")
        return 1
    
    # Load combinations from GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(config.gcs_bucket_name)
    
    # Get latest combinations
    combo_blobs = list(bucket.list_blobs(prefix="combinations/ai_selections/"))
    if not combo_blobs:
        logger.error("No combinations found. Run ai_pairing.py first.")
        return 1
    
    latest_blob = max(combo_blobs, key=lambda b: b.time_created)
    combinations = json.loads(latest_blob.download_as_text())
    
    logger.info(f"Found {len(combinations)} combinations")
    
    # Initialize generator
    generator = ImageGenerator()
    
    # Generate images
    logger.info(f"\nGenerating {config.variations_per_combination} variations per combination...")
    generated_images = await generator.generate_images_for_combinations(
        combinations,
        variations_per_combo=config.variations_per_combination
    )
    
    # Save to GCS
    generator.save_to_gcs(generated_images)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Image generation complete!")
    logger.info(f"Generated {len(generated_images)} image tasks")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))

