#!/usr/bin/env python3
"""
Query Google BigQuery for trending topics.

Uses public datasets to fetch trending topics for US and Italy.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.cloud import bigquery
from google.cloud import storage
from loguru import logger

from scripts.brainrot.config import config

load_dotenv()


class BigQueryTrendsQuery:
    """Query BigQuery for trending topics."""
    
    def __init__(self, project_id: Optional[str] = None):
        """Initialize BigQuery client."""
        self.project_id = project_id or os.getenv("GOOGLE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.client = bigquery.Client(project=self.project_id)
        logger.info(f"Initialized BigQuery client for project: {self.project_id}")
    
    def query_trending_topics(
        self,
        country_code: str,
        weeks: int = 1,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query trending topics for a specific country.
        
        Args:
            country_code: Country code (e.g., "US", "IT")
            weeks: Number of weeks to look back
            limit: Maximum number of results
            
        Returns:
            List of trending topics with metadata
        """
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(weeks=weeks)
        
        # Use parameterized query to avoid SQL injection
        job_config = None
        
        try:
            from google.cloud.bigquery import ScalarQueryParameter, QueryJobConfig
            
            if country_code.upper() == "US":
                # US Query (uses top_terms table, no country_code column)
                # Columns: dma_name, dma_id, term, week, score, rank, refresh_date
                query = f"""
                SELECT 
                    term,
                    score,
                    rank,
                    week
                FROM `{config.bigquery_dataset}.top_terms`
                WHERE 
                    week >= @start_date
                    AND week <= @end_date
                ORDER BY score DESC
                LIMIT @limit
                """
                job_config = QueryJobConfig(
                    query_parameters=[
                        ScalarQueryParameter("start_date", "DATE", start_date.date()),
                        ScalarQueryParameter("end_date", "DATE", end_date.date()),
                        ScalarQueryParameter("limit", "INT64", limit),
                    ]
                )
            else:
                # International Query (uses international_top_terms table)
                # Columns: country_code, region_code, score, rank, refresh_date, country_name, region_name, term, week
                query = f"""
                SELECT 
                    term,
                    score,
                    rank,
                    week
                FROM `{config.bigquery_dataset}.international_top_terms`
                WHERE 
                    country_code = @country_code
                    AND week >= @start_date
                    AND week <= @end_date
                ORDER BY score DESC
                LIMIT @limit
                """
                job_config = QueryJobConfig(
                    query_parameters=[
                        ScalarQueryParameter("country_code", "STRING", country_code),
                        ScalarQueryParameter("start_date", "DATE", start_date.date()),
                        ScalarQueryParameter("end_date", "DATE", end_date.date()),
                        ScalarQueryParameter("limit", "INT64", limit),
                    ]
                )
        except ImportError:
            # Fallback: use simple query without parameters (less secure but works)
            logger.warning("BigQuery parameterized queries not available, using simple query")
            
            if country_code.upper() == "US":
                query = f"""
                SELECT 
                    term,
                    score,
                    rank,
                    week
                FROM `{config.bigquery_dataset}.top_terms`
                WHERE 
                    week >= '{start_date.strftime('%Y-%m-%d')}'
                    AND week <= '{end_date.strftime('%Y-%m-%d')}'
                ORDER BY score DESC
                LIMIT {limit}
                """
            else:
                query = f"""
                SELECT 
                    term,
                    score,
                    rank,
                    week
                FROM `{config.bigquery_dataset}.international_top_terms`
                WHERE 
                    country_code = '{country_code}'
                    AND week >= '{start_date.strftime('%Y-%m-%d')}'
                    AND week <= '{end_date.strftime('%Y-%m-%d')}'
                ORDER BY score DESC
                LIMIT {limit}
                """
        
        try:
            logger.info(f"Querying BigQuery for {country_code} trends (last {weeks} weeks)...")
            if job_config:
                query_job = self.client.query(query, job_config=job_config)
            else:
                query_job = self.client.query(query)
            results = query_job.result()
            
            trends = []
            for row in results:
                trends.append({
                    "term": getattr(row, 'term', ''),
                    "score": getattr(row, 'score', 0),
                    "rank": getattr(row, 'rank', 0),
                    "week": str(getattr(row, 'week', None)) if hasattr(row, 'week') and getattr(row, 'week', None) else None,
                    "country": country_code
                })
            
            logger.info(f"Found {len(trends)} trending topics for {country_code}")
            return trends
            
        except Exception as e:
            logger.error(f"BigQuery query failed: {e}")
            logger.info("Falling back to pytrends for trending topics...")
            # Fallback: return empty list, will use pytrends instead
            return []
    
    def save_to_gcs(
        self,
        data: List[Dict[str, Any]],
        country_code: str,
        data_type: str = "raw"
    ) -> str:
        """Save trending topics data to GCS."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(config.gcs_bucket_name)
        
        # Create filename with timestamp
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
    logger.info("=" * 60)
    logger.info("BigQuery Trends Query")
    logger.info("=" * 60)
    
    query_client = BigQueryTrendsQuery()
    
    # Query for US trends
    logger.info("\nQuerying US trends...")
    us_trends = query_client.query_trending_topics(
        country_code="US",
        weeks=config.time_range_weeks,
        limit=config.max_trending_topics_per_region
    )
    
    if us_trends:
        query_client.save_to_gcs(us_trends, "US", "raw")
        logger.info(f"✅ US trends: {len(us_trends)} topics")
    else:
        logger.warning("⚠️  No US trends found (will use pytrends fallback)")
    
    # Query for Italian trends
    logger.info("\nQuerying Italian trends...")
    it_trends = query_client.query_trending_topics(
        country_code="IT",
        weeks=config.time_range_weeks,
        limit=config.max_trending_topics_per_region
    )
    
    if it_trends:
        query_client.save_to_gcs(it_trends, "IT", "raw")
        logger.info(f"✅ Italian trends: {len(it_trends)} topics")
    else:
        logger.warning("⚠️  No Italian trends found (will use pytrends fallback)")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Query complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
