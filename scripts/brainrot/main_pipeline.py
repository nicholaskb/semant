#!/usr/bin/env python3
"""
Main orchestration pipeline for Brain Rot project.

Runs the complete pipeline:
1. Query trending topics (BigQuery/pytrends)
2. Tokenize trends
3. AI pairing
4. Image generation
"""
import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

from scripts.brainrot.config import config

# Import pipeline modules
from scripts.brainrot.query_bigquery_trends import BigQueryTrendsQuery
from scripts.brainrot.pytrends_fallback import PytrendsTrendsQuery, PYTRENDS_AVAILABLE
from scripts.brainrot.tokenize_trends import TrendTokenizer
from scripts.brainrot.ai_pairing import AIPairingEngine
from scripts.brainrot.generate_images import ImageGenerator

load_dotenv()


class BrainRotPipeline:
    """Main pipeline orchestrator."""
    
    def __init__(self, skip_images: bool = False):
        """Initialize pipeline."""
        self.skip_images = skip_images
        self.results = {
            "start_time": datetime.now().isoformat(),
            "steps_completed": [],
            "errors": []
        }
    
    async def run(self):
        """Run the complete pipeline."""
        logger.info("=" * 60)
        logger.info("🧠 BRAIN ROT PIPELINE")
        logger.info("=" * 60)
        logger.info(f"Configuration:")
        logger.info(f"  - Time range: {config.time_range_weeks} weeks")
        logger.info(f"  - Regions: {config.pytrends_regions}")
        logger.info(f"  - Combinations: {config.combinations_per_run}")
        logger.info(f"  - Image variations: {config.variations_per_combination}")
        logger.info("")
        
        try:
            # Step 1: Query trending topics
            await self._step_1_query_trends()
            
            # Step 2: Tokenize trends
            await self._step_2_tokenize()
            
            # Step 3: AI pairing
            await self._step_3_ai_pairing()
            
            # Step 4: Generate images (optional)
            if not self.skip_images:
                await self._step_4_generate_images()
            else:
                logger.info("⏭️  Skipping image generation (--skip-images)")
            
            self.results["end_time"] = datetime.now().isoformat()
            self.results["status"] = "success"
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ PIPELINE COMPLETE!")
            logger.info("=" * 60)
            logger.info(f"Steps completed: {len(self.results['steps_completed'])}")
            if self.results["errors"]:
                logger.warning(f"Errors encountered: {len(self.results['errors'])}")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.results["status"] = "failed"
            self.results["errors"].append(str(e))
            raise
    
    async def _step_1_query_trends(self):
        """Step 1: Query trending topics."""
        logger.info("📊 STEP 1: Querying Trending Topics")
        logger.info("-" * 60)
        
        try:
            # Try BigQuery first
            bq_client = BigQueryTrendsQuery()
            
            us_trends = bq_client.query_trending_topics(
                "US",
                weeks=config.time_range_weeks,
                limit=config.max_trending_topics_per_region
            )
            
            it_trends = bq_client.query_trending_topics(
                "IT",
                weeks=config.time_range_weeks,
                limit=config.max_trending_topics_per_region
            )
            
            # If BigQuery didn't return results, use pytrends
            if not us_trends or not it_trends:
                if PYTRENDS_AVAILABLE:
                    logger.info("Using pytrends fallback...")
                    pytrends_client = PytrendsTrendsQuery()
                    
                    if not us_trends:
                        us_trends = pytrends_client.get_trending_topics("US", limit=config.max_trending_topics_per_region)
                        if us_trends:
                            pytrends_client.save_to_gcs(us_trends, "US", "raw")
                    
                    if not it_trends:
                        it_trends = pytrends_client.get_trending_topics("IT", limit=config.max_trending_topics_per_region)
                        if it_trends:
                            pytrends_client.save_to_gcs(it_trends, "IT", "raw")
                else:
                    logger.warning("⚠️  No trending data available. Install pytrends: pip install pytrends")
            
            if us_trends:
                bq_client.save_to_gcs(us_trends, "US", "raw")
                logger.info(f"✅ US trends: {len(us_trends)} topics")
            
            if it_trends:
                bq_client.save_to_gcs(it_trends, "IT", "raw")
                logger.info(f"✅ Italian trends: {len(it_trends)} topics")
            
            self.results["steps_completed"].append("query_trends")
            
        except Exception as e:
            logger.error(f"Step 1 failed: {e}")
            self.results["errors"].append(f"Step 1: {str(e)}")
            raise
    
    async def _step_2_tokenize(self):
        """Step 2: Tokenize trends."""
        logger.info("")
        logger.info("🔤 STEP 2: Tokenizing Trends")
        logger.info("-" * 60)
        
        try:
            tokenizer = TrendTokenizer()
            
            # Load trends from GCS
            from google.cloud import storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(config.gcs_bucket_name)
            
            import json
            
            # Process US trends
            us_blobs = list(bucket.list_blobs(prefix="us_trends/raw/"))
            if us_blobs:
                latest_blob = max(us_blobs, key=lambda b: b.time_created)
                try:
                    us_data = json.loads(latest_blob.download_as_text())
                    if not isinstance(us_data, list):
                        logger.warning("US trends data is not a list")
                        us_data = []
                    us_tokens = tokenizer.tokenize_trends(us_data, language="en")
                    if us_tokens:
                        tokenizer.save_to_gcs(us_tokens, "US")
                        logger.info(f"✅ US tokens: {len(us_tokens)}")
                    else:
                        logger.warning("⚠️  No US tokens generated")
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"Failed to process US trends: {e}")
            else:
                logger.warning("⚠️  No US trends found in GCS")
            
            # Process Italian trends
            it_blobs = list(bucket.list_blobs(prefix="italian_trends/raw/"))
            if it_blobs:
                latest_blob = max(it_blobs, key=lambda b: b.time_created)
                try:
                    it_data = json.loads(latest_blob.download_as_text())
                    if not isinstance(it_data, list):
                        logger.warning("Italian trends data is not a list")
                        it_data = []
                    it_tokens = tokenizer.tokenize_trends(it_data, language="it")
                    if it_tokens:
                        tokenizer.save_to_gcs(it_tokens, "IT")
                        logger.info(f"✅ Italian tokens: {len(it_tokens)}")
                    else:
                        logger.warning("⚠️  No Italian tokens generated")
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"Failed to process Italian trends: {e}")
            else:
                logger.warning("⚠️  No Italian trends found in GCS")
            
            self.results["steps_completed"].append("tokenize")
            
        except Exception as e:
            logger.error(f"Step 2 failed: {e}")
            self.results["errors"].append(f"Step 2: {str(e)}")
            raise
    
    async def _step_3_ai_pairing(self):
        """Step 3: AI pairing."""
        logger.info("")
        logger.info("🤖 STEP 3: AI Pairing")
        logger.info("-" * 60)
        
        try:
            # Load tokenized data
            from google.cloud import storage
            import json
            storage_client = storage.Client()
            bucket = storage_client.bucket(config.gcs_bucket_name)
            
            us_blobs = list(bucket.list_blobs(prefix="us_trends/tokenized/"))
            it_blobs = list(bucket.list_blobs(prefix="italian_trends/tokenized/"))
            
            if not us_blobs:
                raise ValueError("Missing US tokenized data. Run step 2 first.")
            if not it_blobs:
                raise ValueError("Missing Italian tokenized data. Run step 2 first.")
            
            us_tokens = json.loads(max(us_blobs, key=lambda b: b.time_created).download_as_text())
            it_tokens = json.loads(max(it_blobs, key=lambda b: b.time_created).download_as_text())
            
            if not us_tokens or not it_tokens:
                raise ValueError("Tokenized data is empty. Check tokenization step.")
            
            # Initialize pairing engine
            engine = AIPairingEngine()
            await engine.initialize()
            
            # Generate combinations
            combinations = await engine.select_best_combinations(
                us_tokens,
                it_tokens,
                num_combinations=config.combinations_per_run
            )
            
            # Save to GCS
            engine.save_to_gcs(combinations)
            
            logger.info(f"✅ Generated {len(combinations)} combinations")
            self.results["steps_completed"].append("ai_pairing")
            self.results["combinations_count"] = len(combinations)
            
        except Exception as e:
            logger.error(f"Step 3 failed: {e}")
            self.results["errors"].append(f"Step 3: {str(e)}")
            raise
    
    async def _step_4_generate_images(self):
        """Step 4: Generate images."""
        logger.info("")
        logger.info("🎨 STEP 4: Generating Images")
        logger.info("-" * 60)
        
        try:
            # Load combinations
            from google.cloud import storage
            import json
            storage_client = storage.Client()
            bucket = storage_client.bucket(config.gcs_bucket_name)
            
            combo_blobs = list(bucket.list_blobs(prefix="combinations/ai_selections/"))
            if not combo_blobs:
                raise ValueError("No combinations found. Run step 3 first.")
            
            latest_combo_blob = max(combo_blobs, key=lambda b: b.time_created)
            combinations = json.loads(latest_combo_blob.download_as_text())
            
            if not isinstance(combinations, list):
                logger.warning("Combinations data is not a list, converting...")
                combinations = [combinations] if combinations else []
            
            # Initialize generator
            generator = ImageGenerator()
            
            # Generate images
            generated_images = await generator.generate_images_for_combinations(
                combinations,
                variations_per_combo=config.variations_per_combination
            )
            
            # Save to GCS
            generator.save_to_gcs(generated_images)
            
            logger.info(f"✅ Generated {len(generated_images)} image tasks")
            self.results["steps_completed"].append("generate_images")
            self.results["images_count"] = len(generated_images)
            
        except Exception as e:
            logger.error(f"Step 4 failed: {e}")
            self.results["errors"].append(f"Step 4: {str(e)}")
            # Don't raise - image generation is optional
            logger.warning("Continuing despite image generation failure...")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Brain Rot Pipeline")
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip image generation step"
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=config.time_range_weeks,
        help=f"Number of weeks to query (default: {config.time_range_weeks})"
    )
    
    args = parser.parse_args()
    
    # Update config if needed
    if args.weeks != config.time_range_weeks:
        config.time_range_weeks = args.weeks
    
    # Run pipeline
    pipeline = BrainRotPipeline(skip_images=args.skip_images)
    
    try:
        asyncio.run(pipeline.run())
        return 0
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

