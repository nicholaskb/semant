#!/usr/bin/env python3
"""
Ingest Brain Rot Trends into Knowledge Graph.

This script:
1. Fetches trending topics using the BigQuery/Pytrends pipeline.
2. Models them as nodes in the Knowledge Graph.
3. Links them to their country/region and metadata.

Schema:
    trend:Trend_{uuid} a trend:Trend ;
        trend:name "Keyword" ;
        trend:country "US" ;
        trend:score 100 ;
        trend:rank 1 ;
        trend:dateCreated "2025-..." .
"""

import asyncio
import uuid
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from rdflib import Namespace, Literal, URIRef, RDF, XSD

# Import internal modules
from kg.models.graph_manager import KnowledgeGraphManager
from scripts.brainrot.query_bigquery_trends import BigQueryTrendsQuery
from scripts.brainrot.config import config

# Load environment variables
load_dotenv()

# Define Namespaces
TREND = Namespace("http://example.org/trend#")
SCHEMA = Namespace("http://schema.org/")

class TrendIngester:
    def __init__(self, kg_manager: KnowledgeGraphManager):
        self.kg = kg_manager
        self.bq_query = BigQueryTrendsQuery()

    async def ingest_trends(self, country_code: str, limit: int = 50):
        """
        Fetch trends for a country and ingest them into the KG.
        """
        print(f"🔍 Fetching top {limit} trends for {country_code}...")
        
        # Fetch trends (this calls BigQuery or fallback)
        # Note: query_trending_topics is synchronous in the referenced script
        try:
            trends = self.bq_query.query_trending_topics(
                country_code=country_code,
                limit=limit
            )
        except Exception as e:
            print(f"❌ Error fetching trends for {country_code}: {e}")
            return

        if not trends:
            print(f"⚠️ No trends found for {country_code}.")
            return

        print(f"📥 Ingesting {len(trends)} trends into Knowledge Graph...")
        
        count = 0
        for item in trends:
            try:
                await self._create_trend_node(item, country_code)
                count += 1
            except Exception as e:
                print(f"   ❌ Failed to ingest trend '{item.get('term', 'unknown')}': {e}")

        print(f"✅ Successfully ingested {count} trends for {country_code}.")

    async def _create_trend_node(self, item: Dict[str, Any], country_code: str):
        """
        Create a single Trend node in the KG.
        """
        term = item.get("term")
        if not term:
            return

        # Generate a unique URI for this specific trend occurrence
        # We include date to distinguish same trend on different days
        trend_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{term}_{country_code}_{datetime.now().date()}"))
        trend_uri = URIRef(TREND[trend_id])

        # Prepare triples
        # 1. Define Type
        await self.kg.add_triple(str(trend_uri), str(RDF.type), str(TREND.Trend))
        
        # 2. Core Properties
        await self.kg.add_triple(str(trend_uri), str(TREND.name), term)
        await self.kg.add_triple(str(trend_uri), str(TREND.country), country_code)
        await self.kg.add_triple(str(trend_uri), str(TREND.dateCreated), datetime.now(timezone.utc).isoformat())

        # 3. Metadata (Score/Rank)
        if "score" in item:
            await self.kg.add_triple(str(trend_uri), str(TREND.score), str(item["score"]))
        
        if "rank" in item:
            await self.kg.add_triple(str(trend_uri), str(TREND.rank), str(item["rank"]))

        # 4. Link to generic Concept (for semantic clustering later)
        # This creates a persistent node for the "Concept" of the keyword, 
        # linking multiple daily trend instances together.
        concept_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, term.lower().strip()))
        concept_uri = URIRef(TREND[f"Concept_{concept_id}"])
        
        await self.kg.add_triple(str(concept_uri), str(RDF.type), str(TREND.Concept))
        await self.kg.add_triple(str(concept_uri), str(TREND.name), term.lower().strip())
        
        # Link Trend -> Concept
        await self.kg.add_triple(str(trend_uri), str(TREND.representsConcept), str(concept_uri))

async def main():
    print("🚀 Starting Trend Ingestion...")
    
    # Initialize KG (persistent)
    kg_manager = KnowledgeGraphManager(persistent_storage=True)
    await kg_manager.initialize()
    
    ingester = TrendIngester(kg_manager)

    # Ingest US Trends
    await ingester.ingest_trends(country_code="US")

    # Ingest Italian Trends
    await ingester.ingest_trends(country_code="IT")

    # Cleanup
    await kg_manager.shutdown()
    print("\n✨ Ingestion Complete!")

if __name__ == "__main__":
    asyncio.run(main())

