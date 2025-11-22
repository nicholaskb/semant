#!/usr/bin/env python3
"""
AI-powered pairing logic using Gemini.

Selects best combinations of Italian phrases and American objects.
"""
import os
import sys
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.cloud import storage
from loguru import logger

from scripts.brainrot.config import config
from scripts.brainrot.sanitize_outputs import sanitize_combinations, sanitize_ai_response
from integrations.vertex_ai_client import get_vertex_client, VertexAIModel

load_dotenv()


class AIPairingEngine:
    """AI engine for pairing Italian phrases with American objects."""
    
    def __init__(self):
        """Initialize AI pairing engine."""
        self.vertex_client = None
        logger.info("Initialized AI Pairing Engine")
    
    async def initialize(self):
        """Initialize Vertex AI client."""
        try:
            self.vertex_client = await get_vertex_client()
            logger.info("✅ Vertex AI client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI client: {e}")
            raise
    
    async def select_best_combinations(
        self,
        american_tokens: List[Dict[str, Any]],
        italian_tokens: List[Dict[str, Any]],
        num_combinations: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Select best combinations from tokens.
        
        Args:
            american_tokens: List of American trending tokens
            italian_tokens: List of Italian trending tokens
            num_combinations: Number of combinations to generate
            
        Returns:
            List of selected combinations with scores
        """
        # Check for empty tokens FIRST to avoid unnecessary initialization
        if not american_tokens or not italian_tokens:
            logger.warning("Empty token lists provided")
            return []
        
        # Only initialize if we have tokens to process
        if not self.vertex_client:
            await self.initialize()
        
        random_american = random.sample(
            american_tokens,
            min(20, len(american_tokens))
        ) if len(american_tokens) > 0 else []
        random_italian = random.sample(
            italian_tokens,
            min(20, len(italian_tokens))
        ) if len(italian_tokens) > 0 else []
        
        if not random_american or not random_italian:
            logger.warning("Not enough tokens for pairing")
            return []
        
        # Extract words
        american_words = [t["word"] for t in random_american]
        italian_words = [t["word"] for t in random_italian]
        
        # Create prompt for AI
        prompt = self._create_pairing_prompt(american_words, italian_words, num_combinations)
        
        # Query Gemini
        try:
            response = await self.vertex_client.generate_text(
                prompt=prompt,
                model=VertexAIModel.PALM_2_TEXT,
                temperature=0.8,
                max_output_tokens=1024
            )
            
            if response.success and response.content:
                # Sanitize AI response before parsing
                sanitized_content = sanitize_ai_response(response.content)
                combinations = self._parse_ai_response(sanitized_content, num_combinations)
                # Sanitize combinations to remove any inner-monologue from explanations
                combinations = sanitize_combinations(combinations)
                logger.info(f"Generated {len(combinations)} combinations")
                return combinations
            else:
                logger.error(f"AI response failed: {response.error_message}")
                return self._fallback_combinations(american_words, italian_words, num_combinations)
                
        except Exception as e:
            logger.error(f"AI pairing failed: {e}")
            return self._fallback_combinations(american_words, italian_words, num_combinations)
    
    def _create_pairing_prompt(
        self,
        american_words: List[str],
        italian_words: List[str],
        num_combinations: int
    ) -> str:
        """Create prompt for AI pairing."""
        return f"""You are an expert at creating viral "Italian brain rot" content - humorous combinations of Italian phrases with American trending objects.

Your task: Select the {num_combinations} BEST combinations from these lists that would create the most viral, humorous, and shareable content.

American trending objects (nouns/verbs):
{', '.join(american_words[:20])}

Italian trending words/phrases:
{', '.join(italian_words[:20])}

Guidelines for "best" combinations:
1. **Humor Potential**: Creates unexpected, absurd, or funny juxtapositions
2. **Viral Potential**: Meme-worthy, shareable, relatable
3. **Cultural Contrast**: Highlights amusing differences between Italian and American culture
4. **Visual Potential**: Can be turned into a compelling image/meme
5. **Simplicity**: Easy to understand and remember

For each combination, provide:
- 2-3 American objects/words
- 1-2 Italian phrases/words
- A brief explanation of why it's funny/viral-worthy (write directly, no thinking process)
- A humor score (1-10)
- A viral potential score (1-10)

IMPORTANT: Return ONLY valid JSON. Do not include any thinking process, reasoning, or explanations outside the JSON structure. Start directly with the opening brace.

Format your response as JSON:
{{
  "combinations": [
    {{
      "american_objects": ["object1", "object2"],
      "italian_phrases": ["phrase1"],
      "explanation": "Why this is funny",
      "humor_score": 8,
      "viral_score": 9,
      "combined_prompt": "Short combined phrase for image generation"
    }}
  ]
}}

Generate exactly {num_combinations} combinations, ranked by viral potential."""
    
    def _parse_ai_response(self, content: str, expected_count: int) -> List[Dict[str, Any]]:
        """Parse AI response into structured combinations."""
        try:
            # Try to extract JSON from response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                combinations = data.get("combinations", [])
                
                # Validate and clean combinations
                cleaned = []
                for combo in combinations[:expected_count]:
                    if not isinstance(combo, dict):
                        continue
                    if "american_objects" in combo and "italian_phrases" in combo:
                        # Ensure lists are not empty
                        if not combo.get("american_objects") or not combo.get("italian_phrases"):
                            continue
                        cleaned.append({
                            "american_objects": combo["american_objects"],
                            "italian_phrases": combo["italian_phrases"],
                            "explanation": combo.get("explanation", ""),
                            "humor_score": int(combo.get("humor_score", 5)),
                            "viral_score": int(combo.get("viral_score", 5)),
                            "combined_prompt": combo.get("combined_prompt", self._create_combined_prompt(combo))
                        })
                
                return cleaned
            else:
                logger.warning("No JSON found in AI response")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Response content: {content[:500]}")
            return []
    
    def _create_combined_prompt(self, combo: Dict[str, Any]) -> str:
        """Create a combined prompt from combination."""
        american_objs = combo.get("american_objects", [])
        italian_phrases = combo.get("italian_phrases", [])
        
        # Ensure we have valid lists
        if not american_objs or not italian_phrases:
            return ""
        
        american = ", ".join(str(x) for x in american_objs)
        italian = ", ".join(str(x) for x in italian_phrases)
        return f"{italian} with {american}"
    
    def _fallback_combinations(
        self,
        american_words: List[str],
        italian_words: List[str],
        num_combinations: int
    ) -> List[Dict[str, Any]]:
        """Fallback: create simple random combinations."""
        combinations = []
        
        for i in range(num_combinations):
            if not american_words or not italian_words:
                break
            american_count = min(2, len(american_words))
            italian_count = min(1, len(italian_words))
            american_selection = random.sample(american_words, american_count) if american_count > 0 else []
            italian_selection = random.sample(italian_words, italian_count) if italian_count > 0 else []
            
            if not american_selection or not italian_selection:
                continue
            
            combinations.append({
                "american_objects": american_selection,
                "italian_phrases": italian_selection,
                "explanation": "Random combination (AI unavailable)",
                "humor_score": random.randint(3, 7),
                "viral_score": random.randint(3, 7),
                "combined_prompt": self._create_combined_prompt({
                    "american_objects": american_selection,
                    "italian_phrases": italian_selection
                })
            })
        
        return combinations
    
    async def generate_italian_phrases(
        self,
        italian_tokens: List[Dict[str, Any]],
        num_phrases: int = 20
    ) -> List[str]:
        """Generate short Italian phrases from tokens."""
        if not self.vertex_client:
            await self.initialize()
        
        # Select random tokens (handle empty list)
        if not italian_tokens:
            logger.warning("No Italian tokens provided")
            return []
        
        sample_size = min(num_phrases, len(italian_tokens))
        if sample_size == 0:
            return []
        
        random_tokens = random.sample(italian_tokens, sample_size)
        words = [t["word"] for t in random_tokens]
        
        prompt = f"""Generate {num_phrases} short, catchy Italian phrases (2-4 words each) using these trending Italian words:
{', '.join(words[:30])}

Make them:
- Modern and relatable
- Meme-worthy and viral
- Can include abbreviations/slang
- Humorous when combined with American objects

IMPORTANT: Return ONLY a valid JSON array. Do not include any thinking process, reasoning, or explanations. Start directly with the opening bracket.

Return as JSON array: ["phrase1", "phrase2", ...]"""
        
        try:
            response = await self.vertex_client.generate_text(
                prompt=prompt,
                model=VertexAIModel.PALM_2_TEXT,
                temperature=0.9,
                max_output_tokens=1000
            )
            
            if response.success and response.content:
                # Sanitize response before parsing
                sanitized_content = sanitize_ai_response(response.content)
                # Parse JSON array
                json_start = sanitized_content.find('[')
                json_end = sanitized_content.rfind(']') + 1
                
                if json_start >= 0 and json_end > json_start:
                    try:
                        phrases_json = sanitized_content[json_start:json_end]
                        phrases = json.loads(phrases_json)
                        if isinstance(phrases, list):
                            return phrases[:num_phrases]
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse phrases JSON: {e}")
            
            # Fallback
            if len(words) < 2:
                return words[:num_phrases] if words else []
            return [f"{words[i]} {words[i+1]}" for i in range(0, min(len(words)-1, num_phrases))]
            
        except Exception as e:
            logger.error(f"Failed to generate Italian phrases: {e}")
            if len(words) < 2:
                return words[:num_phrases] if words else []
            return [f"{words[i]} {words[i+1]}" for i in range(0, min(len(words)-1, num_phrases))]
    
    def save_to_gcs(
        self,
        combinations: List[Dict[str, Any]],
        data_type: str = "ai_selections"
    ) -> str:
        """Save combinations to GCS."""
        # Ensure all combinations are sanitized before saving
        sanitized_combinations = sanitize_combinations(combinations)
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(config.gcs_bucket_name)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"combinations/{data_type}/combinations_{timestamp}.json"
        
        blob = bucket.blob(filename)
        blob.upload_from_string(
            json.dumps(sanitized_combinations, indent=2),
            content_type="application/json"
        )
        
        logger.info(f"Saved {len(sanitized_combinations)} combinations to gs://{config.gcs_bucket_name}/{filename}")
        return filename


async def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("AI Pairing Engine")
    logger.info("=" * 60)
    
    # Load tokenized data from GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(config.gcs_bucket_name)
    
    # Load US tokens
    us_blobs = list(bucket.list_blobs(prefix="us_trends/tokenized/"))
    us_tokens = []
    if us_blobs:
        latest_blob = max(us_blobs, key=lambda b: b.time_created)
        us_tokens = json.loads(latest_blob.download_as_text())
    
    # Load Italian tokens
    it_blobs = list(bucket.list_blobs(prefix="italian_trends/tokenized/"))
    it_tokens = []
    if it_blobs:
        latest_blob = max(it_blobs, key=lambda b: b.time_created)
        it_tokens = json.loads(latest_blob.download_as_text())
    
    if not us_tokens or not it_tokens:
        logger.error("Missing tokenized data. Run tokenize_trends.py first.")
        return 1
    
    # Initialize pairing engine
    engine = AIPairingEngine()
    await engine.initialize()
    
    # Generate combinations
    logger.info(f"\nGenerating {config.combinations_per_run} combinations...")
    combinations = await engine.select_best_combinations(
        us_tokens,
        it_tokens,
        num_combinations=config.combinations_per_run
    )
    
    # Save to GCS
    engine.save_to_gcs(combinations)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Pairing complete!")
    logger.info(f"Generated {len(combinations)} combinations")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    import asyncio
    exit(asyncio.run(main()))

