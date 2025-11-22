#!/usr/bin/env python3
"""
Google Trends integration using pytrends library.

This is a fallback when BigQuery data is not available or as primary source.
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.cloud import storage
from loguru import logger

from scripts.brainrot.config import config

load_dotenv()

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    logger.warning("pytrends not installed. Install with: pip install pytrends")


class PytrendsTrendsQuery:
    """Query Google Trends using pytrends library."""
    
    def __init__(self):
        """Initialize pytrends client."""
        if not PYTRENDS_AVAILABLE:
            raise ImportError("pytrends library not available")
        
        # Initialize pytrends (geo parameter will be set per query)
        self.pytrends = TrendReq(hl='en-US', tz=360)
        logger.info("Initialized pytrends client")
    
    def get_trending_topics(
        self,
        country_code: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get trending topics for a specific country.
        
        Args:
            country_code: Country code (e.g., "US", "IT")
            limit: Maximum number of results
            
        Returns:
            List of trending topics
        """
        try:
            # Map country codes to pytrends geo codes
            geo_map = {
                "US": "US",
                "IT": "IT"
            }
            
            geo_code = geo_map.get(country_code, country_code)
            
            logger.info(f"Fetching trending topics for {country_code} (geo={geo_code})...")
            
            # Get daily trending searches
            # Note: pytrends doesn't have a direct "trending" endpoint
            # We'll use trending_searches() which gets real-time trends
            try:
                # pn parameter expects country code (e.g., 'united_states' or 'italy')
                geo_map_pn = {
                    "US": "united_states",
                    "IT": "italy"
                }
                pn_code = geo_map_pn.get(geo_code, geo_code.lower())
                df = self.pytrends.trending_searches(pn=pn_code)
                
                trends = []
                if df is not None and not df.empty:
                    for idx, row in df.head(limit).iterrows():
                        # Handle different DataFrame structures
                        term_val = row[0] if len(row) > 0 else (row.get(0, '') if isinstance(row, dict) else '')
                        if term_val:
                            trends.append({
                                "term": str(term_val),
                                "rank": idx + 1,
                                "country": country_code,
                                "source": "pytrends",
                                "timestamp": datetime.now().isoformat()
                            })
                
                logger.info(f"Found {len(trends)} trending topics for {country_code}")
                
                # Rate limiting: pytrends has strict rate limits
                time.sleep(1)
                
                return trends
                
            except Exception as e:
                logger.warning(f"trending_searches failed for {geo_code}: {e}")
                logger.info("Trying alternative method: related_queries...")
                
                # Fallback: use a generic search term to get related trends
                # This is less ideal but works as fallback
                return self._get_related_trends(geo_code, limit)
                
        except Exception as e:
            logger.error(f"Failed to get trends for {country_code}: {e}")
            return []
    
    def _get_related_trends(
        self,
        geo_code: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback method to get related trends."""
        # Use common search terms to discover trends
        common_terms = ["news", "trending", "viral", "popular"]
        all_trends = []
        
        for term in common_terms[:2]:  # Limit to avoid rate limits
            try:
                self.pytrends.build_payload([term], geo=geo_code, timeframe='today 3-m')
                related = self.pytrends.related_queries()
                
                if term in related and related[term] and isinstance(related[term], dict) and 'top' in related[term]:
                    df = related[term]['top']
                    if df is not None and not df.empty:
                        for idx, row in df.head(limit // len(common_terms)).iterrows():
                            query_val = row.get('query', '') if isinstance(row, dict) else str(row[0] if len(row) > 0 else '')
                            if query_val:
                                all_trends.append({
                                    "term": str(query_val),
                                    "rank": len(all_trends) + 1,
                                    "country": geo_code,
                                    "source": "pytrends_related",
                                    "timestamp": datetime.now().isoformat()
                                })
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Failed to get related trends for '{term}': {e}")
                continue
        
        return all_trends[:limit]
    
    def save_to_gcs(
        self,
        data: List[Dict[str, Any]],
        country_code: str,
        data_type: str = "raw"
    ) -> str:
        """Save trending topics data to GCS."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(config.gcs_bucket_name)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Map country codes to consistent directory names
        country_dir = "us_trends" if country_code.upper() == "US" else "italian_trends"
        filename = f"{country_dir}/{data_type}/trends_{timestamp}.json"
        
        blob = bucket.blob(filename)
        blob.upload_from_string(
            json.dumps(data, indent=2),
            content_type="application/json"
        )
        
        logger.info(f"Saved {len(data)} trends to gs://{config.gcs_bucket_name}/{filename}")
        return filename


def main():
    """Main execution function."""
    if not PYTRENDS_AVAILABLE:
        logger.error("pytrends library not available. Install with: pip install pytrends")
        return 1
    
    logger.info("=" * 60)
    logger.info("Pytrends Trends Query")
    logger.info("=" * 60)
    
    query_client = PytrendsTrendsQuery()
    
    # Query for US trends
    logger.info("\nQuerying US trends...")
    us_trends = query_client.get_trending_topics(
        country_code="US",
        limit=config.max_trending_topics_per_region
    )
    
    if us_trends:
        query_client.save_to_gcs(us_trends, "US", "raw")
        logger.info(f"✅ US trends: {len(us_trends)} topics")
    
    # Query for Italian trends
    logger.info("\nQuerying Italian trends...")
    it_trends = query_client.get_trending_topics(
        country_code="IT",
        limit=config.max_trending_topics_per_region
    )
    
    if it_trends:
        query_client.save_to_gcs(it_trends, "IT", "raw")
        logger.info(f"✅ Italian trends: {len(it_trends)} topics")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Query complete!")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())

